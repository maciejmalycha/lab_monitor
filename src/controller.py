
from sensors import SSHiLoSensors
from database import SensorsDAO

import time
import logging
import threading
import sys

class ILoController:

    def __init__(self):
        self.log = logging.getLogger('lab_monitor.controller.ILoController')

        self.log.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #ch.setFormatter(formatter)
        self.log.addHandler(ch)

        self.log.info("Initializing...")

        self.db = SensorsDAO()
        self.log.debug("Database opened")

        self.servers = []
        for serv in self.db.server_list():
            try:
                conn = SSHiLoSensors(serv['addr'])
            except Exception as e:
                self.log.error("Cannot connect to %s: %s", serv['addr'], e)
                continue

            self.servers.append(conn)
            self.log.debug("Connected to %s", conn.host)

        if len(self.servers) == 0:
            self.log.info("Nothing to monitor, exitting")
            sys.exit()

    def store_data(self, server):
        self.log.info("Checking %s...", server.host)

        self.log.debug("Loading status of %s...", server.host)
        server_status = server.server_status()
        self.log.debug("Storing status of %s...", server.host)
        self.db.store_server_status(server.host, server_status)

        self.log.debug("Loading power usage of %s...", server.host)
        power_use = server.power_use()
        self.log.debug("Storing power usage of %s...", server.host)
        self.db.store_power_usage(server.host, power_use['present'], power_use['avg'], power_use['min'], power_use['max'])

        self.log.debug("Loading power units of %s...", server.host)
        power_units = server.power_units()
        i = 0
        for power_supply, state in power_units.iteritems():
            i+=1
            self.log.debug("Storing power unit %u/%u of %s...", i, len(power_units), server.host)
            self.db.store_power_unit(server.host, power_supply, state['operational'], state['health'])

        self.log.debug("Loading temperature of %s...", server.host)
        temp_sensors = server.temp_sensors()
        i = 0
        for sensor, reading in temp_sensors.iteritems():
            i+=1
            self.log.debug("Storing temperature sensor %u/%u of %s...", i, len(temp_sensors), server.host)
            self.db.store_temperature(server.host, sensor, reading)

        self.log.info("Finished checking %s", server.host)

    def main_loop(self):
        self.loop = True
        try:
            while self.loop:

                t0 = time.time()

                threads = []
                for server in servers:
                    t = threading.Thread(target=self.store_data, args=(server,))
                    t.start()
                    threads.append(t)

                for t in threads:
                    t.join()

                t = time.time()
                dt = t-t0
                wait = 60-dt

                # wait until next minute
                self.log.debug("Waiting %u seconds...", wait)
                time.sleep(wait)


                
        except KeyboardInterrupt:
            self.log.info("Interrupt detected, exiting")
            self.loop = False

if __name__ == '__main__':
    contr = ILoController()
    contr.main_loop()
