import logging
import time

import gevent

from sensors import SSHiLoSensors
from database import *

class ILoController:

    def __init__(self):
        self.state = "starting..."
        self.state_stream = None
        self.sleep = None
        self.servers_dao = None # you can assign it after instantiating the controller,
        self.sensors_dao = None # if you don't, connection will be automatically established later

        self.loop = False

        self.log = logging.getLogger('lab_monitor.controller.ILoController')
    
    def start(self):
        """Establishes all necessary connections and activates the main loop"""

        self.update_state("starting...")

        self.log.info("Initializing")

        if self.servers_dao is None:
            self.servers_dao = ServersDAO()
        if self.sensors_dao is None:
            self.sensors_dao = SensorsDAO()

        self.log.info("Database opened")

        def conn(serv):
            try:
                conn = SSHiLoSensors(serv['addr'])
            except Exception as e:
                self.log.error("Cannot connect to %s: %s", serv['addr'], e)
                raise

            return conn

        server_list = self.servers_dao.server_list()

        connect = [gevent.spawn(conn, serv) for serv in server_list]
        gevent.joinall(connect)
        self.servers = [job.value for job in connect if job.successful()]
        
        if len(self.servers)==len(server_list):
            self.log.info("Connected to all %u servers", len(self.servers))
        elif self.servers:
            self.log.warning("Connected to %u out of %u servers", len(self.servers), len(server_list))
        else:
            self.log.warning("Nothing to monitor")
            self.update_state("off")
            return

        self.main_loop()

    def update_state(self, state):
        """Sets new controller state (starting, working, idle, stopping, off) and pushes it to a stream, if available"""
        self.state = state
        if self.state_stream is not None:
            self.state_stream.write(self.state)

    def store_data(self, server):
        """Loads sensor and status data from given server (SSHiLoSensors instance) and stores them in the database"""
        self.log.info("Checking %s...", server.host)

        try:
            server_status = server.server_status()
            self.sensors_dao.store_server_status(server.host, server_status)

            power_use = server.power_use()
            self.sensors_dao.store_power_usage(server.host, power_use['present'], power_use['avg'], power_use['min'], power_use['max'])

            power_units = server.power_units()
            for power_supply, state in power_units.iteritems():
                self.sensors_dao.store_power_unit(server.host, power_supply, state['operational'], state['health'])

            temp_sensors = server.temp_sensors()
            for sensor, reading in temp_sensors.iteritems():
                self.sensors_dao.store_temperature(server.host, sensor, reading)

            self.log.info("Finished checking %s", server.host)

        except HostUnreachableException:
            # it has already been logged
            self.sensors_dao.store_server_status(server.host, False)
            return

    def main_loop(self):
        """Calls self.store_data for each server defined (each one in a new gevent.Greenlet) every minute"""
        self.loop = True
        try:
            while self.loop:
                try:
                    t0 = time.time()

                    self.update_state("working")

                    tasks = [gevent.spawn(self.store_data, server) for server in self.servers]
                    gevent.joinall(tasks)

                    t = time.time()
                    dt = t-t0
                    wait = 60-dt


                    # wait until next minute, unless it's time to finish
                    if self.loop and wait>0:
                        self.update_state("idle")
                        self.log.info("Waiting %u seconds...", wait)
                        # it should sleep, but also be able to wake up when stop is called
                        self.sleep = gevent.spawn(gevent.sleep, wait)
                        self.sleep.join()

                except Exception as e:
                    self.log.exception("Exception happened: %s", e)

            self.update_state("off")
            self.log.info("Exiting")
            return True
                
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stops the main loop. If the controller is working, waits until the end of current iteration. If it's idle, breaks out of sleep immediately"""

        if self.loop:
            self.log.info("Stop called")
            self.loop = False
            self.update_state("stopping")
            if self.sleep is not None:
                self.sleep.kill()
        else:
            self.log.info("Already outside main loop")
