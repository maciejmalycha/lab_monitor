import random

class HostUnreachableException(Exception):
    pass

class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        pass
    
    def server_status(self):
        return random.random()>0.7

    def power_use(self):
        return {'present': 316, 'average': 315, 'minimum': 314, 'maximum': 330}

    def power_units(self):
        data = {}
        for component in ['Power Supply 1', 'Power Supply 2']:
            state = random.random()>0.4

            data[component] = {
                'operational': state,
                'health': state
            }

        return data

    def temp_sensors(self):
        data = {}

        for component, mean in {'Ambient Zone': 18, 'Power Supply Zone': 40}.iteritems():
            data[component] = int(random.gauss(mean, 2))

        return data