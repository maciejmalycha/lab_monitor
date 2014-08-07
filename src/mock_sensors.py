
class HostUnreachableException(Exception):
    pass

class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        pass
    
    def server_status(self):
        status = raw_input("Status [1/0]:")
        return bool(status)

    def power_use(self):
        power_use = raw_input("Power usage [present avg min max]: ")
        psplit = power_use.split()
        data = dict((k,psplit[i]) for (i,k) in enumerate(['present', 'avg', 'min', 'max']))
        return data

    def power_units(self):
        data = {}
        for component in ['Power Supply 1', 'Power Supply 2']:
            state = bool(raw_input(component+" [1/0]: "))

            data[component] = {
                'operational': state,
                'health': state
            }

        return data

    def temp_sensors(self):
        data = {}

        for component in ['Ambient Zone']:
            data[component] = int(raw_input(component+": "))

        return data