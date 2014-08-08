import datetime

## BASE ALARMS ##

class Alarm:
    """An alarm is used to keep track of changing parameters in the system."""

    on_message = ""
    off_message = ""

    def __init__(self, master, resource, engine, delay, **kwargs):
        self.master = master
        self.children = []
        if self.master is not None:
            self.master.register(self)
        self.resource = resource
        self.resource.register_alarm(self)
        self.notification_engine = engine
        self.delay = datetime.timedelta(seconds=delay)

        self.active = False
        self.changed = datetime.datetime.now()
        self.kwargs = {}
        self.kwargs.update(kwargs)
        self.sent = True

    def update(self, active, **kwargs):
        """Sets the alarm state to active or inactive;
        optional **kwargs will be formatted into the message"""
        self.kwargs.update(kwargs)
        if self.active != active:
            self.sent = False
            self.active = active
            self.changed = datetime.datetime.now()
            if self.master is not None:
                self.master.check()

        self.notify()

    def notify(self):
        now = datetime.datetime.now()
        if self.master is not None and self.master.active == self.active:
            return
        if not self.sent and (now - self.changed) > self.delay:
            msg = self.on_message if self.active else self.off_message
            self.notification_engine.send(msg.format(**self.kwargs))
            self.sent = True

    def check(self):
        """Default behaviour for a master alarm is to update its state basing
        on states of children alarms. Children alarms should override it,
        master alarms don't need to, unless it's necessary
        to implement additional behaviour."""
        if self.children:
            total = len(self.children)
            count = len(filter(lambda x: x.active, self.children))
            self.update(2 * count > total)

    def register(self, child):
        self.children.append(child)


class ShutdownAlarm(Alarm):
    """Use this class as a mixin to add method for shutting down resource
    if alarm has been active for specified time"""

    shutdown_message = "Shutting down unknown resource" # consider this abstract

    def check(self):
        Alarm.check(self)
        self.shutdown()

    def shutdown(self):
        now = datetime.datetime.now()
        if self.active and (now - self.changed) > datetime.timedelta(minutes=self.kwargs['number']):
            if self.hypervisor is not None:
                self.notification_engine.send(self.shutdown_message.format(**self.kwargs))
                self.resource.hypervisor.force_shutdown()
            else:
                self.notification_engine.send("Hypervisor for {resource} not available".format(self.resource))


## SERVER ALARMS ##

class ConnectionAlarm(Alarm):

    on_message = "Connection with {server} lost. Last reading from {date}"
    off_message = "Connection with {server} restored"

    def check(self):
        self.kwargs['date'] = self.resource.last_reading
        self.update(datetime.datetime.now() - self.kwargs['date'] > datetime.timedelta(minutes=self.kwargs['threshold']))


class UPSServerPowerAlarm(Alarm):

    on_message = "Partial power loss in server {server} detected. Suspected PDU 1 failure"
    off_message = "Power restored in server {server}"

    def check(self):
        self.update(self.resource.power_units['Power Supply 1']['health'] 
                     and self.resource.power_units['Power Supply 1']['operational'])


class GridServerPowerAlarm(Alarm):

    on_message = "Partial power loss in server {server} detected. Suspected PDU 2 failure"
    off_message = "Power restored in server {server}"

    def check(self):
        self.update(self.resource.power_units['Power Supply 2']['health'] 
                     and self.resource.power_units['Power Supply 2']['operational'])


class TemperatureAlarm(Alarm):

    on_message = "Temperature of {server} at {sensor} reached {reading} C"
    off_message = "Temperature of {server} at {sensor} dropped to {reading} C"

    def check(self):
        self.kwargs['reading'] = self.resource.temperature[self.kwargs['sensor']]
        self.update(self.kwargs['reading'] > self.kwargs['threshold'])


class TemperatureShutdownAlarm(TemperatureAlarm, ShutdownAlarm):

    on_message = "Temperature of {server} at {sensor} reached {reading} C. Shutdown in {number} minutes."
    off_message = "Temperature of {server} at {sensor} dropped to {reading} C"
    shutdown_message = "Shutting down {server}"

    def check(self):
        TemperatureAlarm.check(self)
        self.shutdown()


## RACK ALARMS ##

class UPSRackPowerAlarm(ShutdownAlarm):

    on_message = "Partial power loss in rack {rack} detected. Suspected UPS failure. Shutdown in {number} minutes."
    off_message = "Power restored in rack {rack}"
    shutdown_message = "Shutting down rack {rack}"


class GridRackPowerAlarm(ShutdownAlarm):

    on_message = "Partial power loss in rack {rack} detected. Suspected power grid failure. Shutdown in {number} minutes."
    off_message = "Power restored in rack {rack}"
    shutdown_message = "Shutting down rack {rack}"


class RackTemperatureAlarm(ShutdownAlarm):

    on_message = "Temperature in rack {rack} raised. Shutdown in {number} minutes."
    off_message = "Temperature in rack {rack} raised"
    shutdown_message = "Shutting down rack {rack}"


## LAB ALARMS ##

class UPSLabPowerAlarm(ShutdownAlarm):

    on_message = "Partial power loss in lab detected. Suspected UPS failure. Shutdown in {number} minutes."
    off_message = "Power restored in lab"
    shutdown_message = "Shutting down lab"


class GridLabPowerAlarm(ShutdownAlarm):

    on_message = "Partial power loss in lab detected. Suspected power grid failure. Shutdown in {number} minutes."
    off_message = "Power restored in lab"
    shutdown_message = "Shutting down lab"


class LabTemperatureAlarm(ShutdownAlarm):

    on_message = "Temperature in lab raised. Shutdown in {number} minutes."
    off_message = "Temperature in lab raised"
    shutdown_message = "Shutting down lab"