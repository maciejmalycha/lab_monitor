from collections import defaultdict
import string

class Alarm(object):
    """An alarm is used to keep track of changing parameters in the system.
    Each one belongs to a specific group of related alarms, has certain priority
    and a text message (with str.format-compatible keyword placeholders)
    for active and inactive state."""

    instances = defaultdict(list)

    def __init__(self, group, priority, on_message, off_message, **kwargs):
        self.priority = priority
        self.group = group
        self.on_message = on_message
        self.off_message = off_message

        self.active = False
        self.kwargs = defaultdict(lambda: 'N/A')
        self.kwargs.update(kwargs)
        self.sent = True

        Alarm.instances[self.group].append(self)

    def update(self, active, **kwargs):
        """Sets the alarm state to active or inactive;
        optional **kwargs will be formatted into the message"""
        if self.active != active:
            self.sent = False

        self.active = active
        self.kwargs.update(kwargs)

    def activate(self, **kwargs):
        self.update(True, **kwargs)

    def deactivate(self, **kwargs):
        self.update(False, **kwargs)

    def check_send(self):
        """Decides whether the alarm has been updated recently
        and should be sent. If so, marks the alarm as sent."""
        if self.sent:
            return False
        else:
            self.sent = True
            return True

    def __nonzero__(self):
        """Returns True if the alarm is active, otherwise False"""
        return self.active

    def __str__(self):
        """Returns a formatted on/off message."""
        msg = self.on_message if self.active else self.off_message
        return string.Formatter().vformat(msg, (), self.kwargs)


class TemperatureAlarm(Alarm):
    """A special alarm for temperature readings"""

    def __init__(self, priority, threshold,
                 on_message="Temperature of {server} at {sensor} reached {reading} C",
                 off_message="Temperature of {server} at {sensor} dropped to {reading} C",
                 **kwargs):
        super(TemperatureAlarm, self).__init__(
            'temperature', priority, on_message, off_message, **kwargs
        )
        self.reading = None
        self.threshold = threshold

    def update(self, reading):
        self.reading = reading
        super(TemperatureAlarm, self) \
            .update(self.reading>=self.threshold,reading=self.reading)


class Sender(object):
    """A trivial sender for testing purposes"""
    def send(self, msg):
        print msg


class Notifications(object):
    """Pushes notifications about updated alarms via senders
    (objects with send method)."""
    def __init__(self):
        self.senders = []

    def add_sender(self, sender):
        self.senders.append(sender)

    def notify(self):
        """Sends active alarm of the highest priority from each group.
        This method must be called manually after updating all alarms."""
        for group, alarms in Alarm.instances.iteritems():
            for alarm in sorted(alarms, key=lambda x: -x.priority):
                if alarm.check_send():
                    for sender in self.senders:
                        sender.send(str(alarm))
                    break


