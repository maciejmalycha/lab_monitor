import logging
import random
import time

class HostUnreachableException(Exception):
    pass

class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        self.host = host
        self.user = user
        self.password = password
        self.sensors = []
        self.power_supplies = []

        self.log = logging.getLogger('lab_monitor.mock_sensors.SSHiLoSensors')
        self.log.info("Initializing")

        self.connect()
        self.detect_components()

    def connect(self):
        self.log.info("Connecting to the iLo server at %s", self.host)
        time.sleep(random.uniform(1, 3))

    def disconnect(self):
        self.log.info("Disconnecting from the iLo server")

    def detect_components(self):
        time.sleep(random.uniform(0.5, 2))
        self.log.info("Detecting components")

        self.sensors = {'Ambient Zone': 18, 'Power Supply Zone': 40}
        self.power_supplies = ['Power Supply 1', 'Power Supply 2']

        self.log.info("Found %u temperature sensors and %u power supplies", len(self.sensors), len(self.power_supplies))
    
    def server_status(self):
        self.log.info("Checking status")
        time.sleep(random.uniform(0.5, 2))
        return random.random()>0.7

    def power_use(self):
        self.log.info("Checking power usage")
        time.sleep(random.uniform(0.5, 2))
        return {'present': 316, 'average': 315, 'minimum': 314, 'maximum': 330}

    def power_units(self):
        self.log.info("Checking power units")
        data = {}
        for component in self.power_supplies:
            time.sleep(random.uniform(0.5, 2))
            state = random.random()>0.4

            data[component] = {
                'operational': state,
                'health': state
            }

        return data

    def temp_sensors(self):
        self.log.info("Checking temperature")
        data = {}

        for component, mean in self.sensors.iteritems():
            time.sleep(random.uniform(0.5, 2))
            data[component] = int(random.gauss(mean, 2))

        return data