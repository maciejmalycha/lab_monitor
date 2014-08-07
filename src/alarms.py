import datetime


class Alarm:
    """An alarm is used to keep track of changing parameters in the system.
    Each one belongs to a specific group of related alarms, has certain priority
    and a text message (with str.format-compatible keyword placeholders)
    for active and inactive state."""

    on_message = ""
    off_message = ""

    def __init__(self, master, resource, engine, delay, **kwargs):
        self.master = master
        self.children = []
        self.master.register(self)
        self.resource = resource
        self.notification_engine = engine
        self.delay = delay

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
        pass

    def register(self, child):
        self.children.append(child)


class ConnectionAlarm(Alarm):

    on_message = "Connection with {server} lost. Last reading from {date}"
    off_message = "Connection with {server} restored"

    def check(self):
        self.kwargs['date'] = self.resource.last_update
        self.update(self.kwargs['date'] > self.kwargs['threshold'])


class UPSServerPowerAlarm(Alarm):

    on_message = "Partial power loss in server {server} detected. Suspected PDU 1 failure"
    off_message = "Power restored in server {server}"

    def check(self):
        self.update(self.resource.power_units[0])


class GridServerPowerAlarm(Alarm):

    on_message = "Partial power loss in server {server} detected. Suspected PDU 2 failure"
    off_message = "Power restored in server {server}"

    def check(self):
        self.update(self.resource.power_units[1])


class UPSRackPowerAlarm(Alarm):

    on_message = "Partial power loss in rack {rack} detected. Suspected UPS failure. Shutdown in {number} minutes."
    off_message = "Power restored in rack {rack}"

    def check(self):
        total = len(self.children)
        count = len([alarm for alarm in self.children if alarm.active])
        self.update(2 * count > total)


class GridRackPowerAlarm(Alarm):

    on_message = "Partial power loss in rack {rack} detected. Suspected power grid failure"
    off_message = "Power restored in rack {rack}"

    def check(self):
        total = len(self.children)
        count = len([alarm for alarm in self.children if alarm.active])
        self.update(2 * count > total)

        now = datetime.datetime.now()
        if self.active and (now - self.changed) > 60 * self.kwargs['number']:
            self.notification_engine.send("Shutting down rack {rack}".format(**self.kwargs))
            self.resource.force_shutdown()


class TemperatureAlarm(Alarm):

    on_message = "Temperature of {server} at {sensor} reached {reading} C"
    off_message = "Temperature of {server} at {sensor} dropped to {reading} C"

    def check(self):
        self.kwargs['reading'] = self.resource.temperature[self.sensor]
        self.update(self.kwargs['reading'] > self.kwargs['threshold'])


