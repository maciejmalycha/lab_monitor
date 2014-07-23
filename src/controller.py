
from sensors import SSHiLoSensors
from database import *

import logging
import sys

import gevent
from gevent import monkey

monkey.patch_all()

STATECHANGE = 9
logging.addLevelName(STATECHANGE, 'STATECHANGE')

class ILoController:

    def __init__(self, log_handlers=[]):
        self.state = 'starting...'
        self.sleep = None

        self.log = logging.getLogger('lab_monitor.controller.ILoController')
        # TODO: register handlers somewhere else
        for handler in log_handlers:
            self.log.addHandler(handler)
        self.log.setLevel(STATECHANGE)
        

        self.update_state('starting...')

        self.log.info("Initializing...")

        self.servers_dao, self.sensors_dao = ServersDAO(), SensorsDAO()
        self.log.debug("Database opened")

        self.servers = []
        for serv in self.servers_dao.server_list():
            try:
                conn = SSHiLoSensors(serv['addr'])
            except Exception as e:
                self.log.error("Cannot connect to %s: %s", serv['addr'], e)
                continue

            self.servers.append(conn)
            self.log.debug("Connected to %s", conn.host)

        if len(self.servers)==0:
            self.log.info("Nothing to monitor")

    def update_state(self, state):
        self.state = state
        self.log.log(STATECHANGE, self.state)

    def store_data(self, server):
        self.log.info("Checking %s...", server.host)

        self.log.debug("Loading status of %s...", server.host)
        server_status = server.server_status()
        self.log.debug("Storing status of %s...", server.host)
        self.sensors_dao.store_server_status(server.host, server_status)

        self.log.debug("Loading power usage of %s...", server.host)
        power_use = server.power_use()
        self.log.debug("Storing power usage of %s...", server.host)
        self.sensors_dao.store_power_usage(server.host, power_use['present'], power_use['avg'], power_use['min'], power_use['max'])

        self.log.debug("Loading power units of %s...", server.host)
        power_units = server.power_units()
        i = 0
        for power_supply, state in power_units.iteritems():
            i+=1
            self.log.debug("Storing power unit %u/%u of %s...", i, len(power_units), server.host)
            self.sensors_dao.store_power_unit(server.host, power_supply, state['operational'], state['health'])

        self.log.debug("Loading temperature of %s...", server.host)
        temp_sensors = server.temp_sensors()
        i = 0
        for sensor, reading in temp_sensors.iteritems():
            i+=1
            self.log.debug("Storing temperature sensor %u/%u of %s...", i, len(temp_sensors), server.host)
            self.sensors_dao.store_temperature(server.host, sensor, reading)

        self.log.info("Finished checking %s", server.host)

    def main_loop(self):
        if len(self.servers)==0:
            self.update_state('off')
            return False

        self.loop = True
        try:
            while self.loop:

                try:
                    t0 = time.time()

                    self.update_state('working')

                    tasks = [gevent.spawn(self.store_data, server) for server in self.servers]
                    gevent.joinall(tasks)

                    t = time.time()
                    dt = t-t0
                    wait = 60-dt

                    self.update_state('idle')

                    # wait until next minute, unless it's time to finish
                    if self.loop:
                        self.log.debug("Waiting %u seconds...", wait)
                        # it should sleep, but also be able to wake up when stop is called
                        self.sleep = gevent.spawn(gevent.sleep, wait)
                        self.sleep.join()

                except e:
                    self.log.exception("Exception happened: %s", e)

            self.update_state('off')
            self.log.info("Exiting")
            return True
                
        except KeyboardInterrupt:
            self.log.info("Interrupt detected")

    def stop(self):
        if self.loop:
            self.log.info("Stop called")
            self.loop = False
            if self.sleep is not None:
                self.sleep.kill()
        else:
            self.log.info("Already outside main loop")

if __name__ == '__main__':
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    contr = ILoController(log_handlers=[ch])
    contr.main_loop()
