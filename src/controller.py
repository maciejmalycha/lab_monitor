
from sensors import SSHiLoSensors
from database import SensorsDAO
from sys import stdout
from datetime import datetime

class ILoController:

    def __init__(self):
        self.db = SensorsDAO()
        self.servers = []
        self.log_stream = None

    def set_logging(self, log_stream):
        self.log_stream = log_stream

    def log(self, message):
        if self.log_stream is not None:
            self.log_stream.write("[ %s ] %s\n"%(datetime.now(), message))

    def add_server(self, host, username, password):
        self.log("Adding %s to watched servers..."%host)
        try:
            server = SSHiLoSensors(host, username, password)
            self.servers.append(server)
        except:
            self.log("Connection failed!")
        self.log("Successfully connected to %s"%host)

    def store_data(self):
        for server in self.servers:
            self.log("Checking %s..."%server.host)

            self.log("Loading status...")
            server_status = server.server_status()
            self.log("Storing status...")
            self.db.store_server_status(server.host, server_status)

            self.log("Loading power usage...")
            power_use = server.power_use()
            self.log("Storing power usage...")
            self.db.store_power_usage(server.host, power_use['present'], power_use['avg'], power_use['min'], power_use['max'])

            self.log("Loading power units...")
            power_units = server.power_units()
            i = 0
            for power_supply, state in power_units.iteritems():
                i+=1
                self.log("Storing power unit %u/%u..."%(i,len(power_units)))
                self.db.store_power_unit(server.host, power_supply, state['operational'], state['health'])

            self.log("Loading temperature...")
            temp_sensors = server.temp_sensors()
            i = 0
            for sensor, reading in temp_sensors.iteritems():
                i+=1
                self.log("Storing temperature sensor %u/%u..."%(i,len(temp_sensors)))
                self.db.store_temperature(server.host, sensor, reading)

            self.log("Finished checking %s"%server.host)

    def main_loop(self):
        self.loop = True
        try:
            while self.loop:
                self.store_data()
        except KeyboardInterrupt:
            self.log("Interrupt detected, exiting")
            self.loop = False

if __name__ == '__main__':
    contr = ILoController()
    contr.set_logging(stdout)

    contr.add_server('pl-byd-esxi13-ilo', 'Administrator', 'ChangeMe')

    contr.main_loop()
