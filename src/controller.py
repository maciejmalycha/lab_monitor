
from minuteworker import MinuteWorker
from sensors import SSHiLoSensors
from database import *

class ILoController(MinuteWorker):
    logger_name = 'lab_monitor.controller.ILoController'

    def __init__(self):
        super(ILoController, self).__init__()
        self.servers_dao = None # you can assign it after instantiating the controller,
        self.sensors_dao = None # if you don't, connection will be automatically established later
    
    def start(self):
        """Establishes all necessary connections and activates the main loop"""

        self.update_state("starting...")

        self.log.info("Initializing")

        if self.servers_dao is None:
            self.servers_dao = ServersDAO()
        if self.sensors_dao is None:
            self.sensors_dao = SensorsDAO()

        self.log.info("Database opened")

        self.servers = []
        server_list = self.servers_dao.server_list()
        for serv in server_list:
            try:
                conn = SSHiLoSensors(serv['addr'])
            except Exception as e:
                self.log.error("Cannot connect to %s: %s", serv['addr'], e)
                continue
            self.servers.append(conn)
        
        if len(self.servers)==len(server_list):
            self.log.info("Connected to all %u servers", len(self.servers))
        elif self.servers:
            self.log.warning("Connected to %u out of %u servers", len(self.servers), len(server_list))
        else:
            self.log.warning("Nothing to monitor")
            self.update_state("off")
            return

        self.main_loop()

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

    def tasks(self):
        return [(self.store_data, (server,)) for server in self.servers]