

class Signal:
    pass

class RackSignal(Signal):
    def __init__(self, signals):
        self.signals = signals
        self.rack_id = self.signals[0].server['rack']

class ServerShutdownSignal(Signal):
    """A base class for server signals that require shutdown"""
    pass

class RackShutdownSignal(RackSignal):
    """A base class for rack signals that require shutdown"""
    pass

class LabShutdownSignal(Signal):
    """A base class for lab signals that require shutdown"""
    pass

# # # # # # # # # # # # # # # # # # # # # # # # # # # #

class ServerCommunicationRestoredSignal(Signal):
    def __init__(self, server):
        self.server = server
    def __str__(self):
        return "Communication with server {0} restored".format(self.server['addr'])

class ServerCommunicationLostSignal(Signal):
    def __init__(self, server, last_reading):
        self.server = server
        self.last_reading = last_reading
    def __str__(self):
        return "Communication with server {0} lost. Last reading from {1}".format(self.server['addr'], self.last_reading)

class ServerUPSPowerLossSignal(Signal):
    PARENT = 'RackUPSPowerLossSignal'
    def __init__(self, server):
        self.server = server
    def __str__(self):
        return "Power loss in UPS supply in server {0}".format(self.server['addr'])

class ServerGridPowerLossSignal(Signal):
    PARENT = 'RackGridPowerLossSignal'
    def __init__(self, server):
        self.server = server
    def __str__(self):
        return "Power loss in power grid supply in server {0}".format(self.server['addr'])

class ServerPowerRestoredSignal(Signal):
    PARENT = 'RackPowerRestoredSignal'
    def __init__(self, server):
        self.server = server
    def __str__(self):
        return "Power loss in power grid supply in server {0}".format(self.server['addr'])

class ServerTemperatureRaiseSignal(Signal):
    PARENT = 'RackTemperatureRaiseSignal'
    sensor = 'unknown sensor'
    def __init__(self, server, value):
        self.server = server
        self.value = value
    def __str__(self):
        return "Temperature at {0} in server {1} reached {2} C".format(self.sensor, self.server['addr'], self.value)

class ServerTemperatureDropSignal(Signal):
    PARENT = 'RackTemperatureDropSignal'
    sensor = 'unknown sensor'
    def __init__(self, server, value):
        self.server = server
        self.value = value
    def __str__(self):
        return "Temperature at {0} in server {1} dropped to {2} C".format(self.sensor, self.server['addr'], self.value)

class ServerTemperatureShutdownSignal(ServerShutdownSignal):
    PARENT = 'RackTemperatureShutdownSignal'
    sensor = 'unknown sensor'
    def __init__(self, server, value):
        self.server = server
        self.value = value
    def __str__(self):
        return "Temperature at {0} in server {1} reached {2} C. Shutting down.".format(self.sensor, self.server['addr'], self.value)

class ServerTemperatureSignalsFactory:
    """In order to store temperature signals as different classes (necessary for grouping)
    this class provides creation of new temperature signal class for given sensor"""

    classes = {}
    @classmethod
    def create(cls, base, sensor):
        try:
            return cls.classes[base, sensor]
        except KeyError:
            class NewSignal(base):
                pass
            NewSignal.__name__ = "{0}[{1}]".format(base.__name__, sensor)
            NewSignal.sensor = sensor
            cls.classes[base, sensor] = NewSignal
            return NewSignal

class ServerShutdownInitSignal(Signal):
    def __init__(self, server_list, server_name):
        pass

class ServerShutdownCompletedSignal(Signal):
    def __init__(self, server_list, server_name):
        pass

# # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class RackUPSPowerLossSignal(RackSignal):
    def __str__(self):
        return "Power loss in rack {0}. Suspected UPS failure".format(self.rack_id+1) # internally, rack numbers are zero-based

class RackGridPowerLossSignal(RackSignal):
    def __str__(self):
        return "Power loss in rack {0}. Suspected power grid failure".format(self.rack_id+1)

class RackUPSPowerRestoredSignal(RackSignal):
    def __str__(self):
        return "Power restored in rack {0}".format(self.rack_id+1)

class RackTemperatureRaiseSignal(RackSignal):
    def __str__(self):
        return "Temperature in rack {0} raised".format(self.rack_id+1)

class RackTemperatureDropSignal(RackSignal):
    def __str__(self):
        return "Temperature in rack {0} dropped".format(self.rack_id+1)

class RackTemperatureShutdownSignal(RackShutdownSignal):
    def __str__(self):
        return "Temperature in rack {0} reached too much. Shutting down".format(self.rack_id+1)

# # # # # # # # # # # # # # # # # # # # # # # # # # # #

class LabPowerPartialLossSignal(Signal):
    def __init__(self, timeout):
        pass

class LabPowerRestoredSignal(Signal):
    def __init__(self):
        pass

class LabTemperatureRaiseSignal(Signal):
    def __init__(self, temp_value):
        pass

class LabTemperatureDropSignal(Signal):
    def __init__(self, temp_value):
        pass

class LabTemperatureShutdownSignal(Signal):
    def __init__(self, temp_val):
        pass
