from collections import defaultdict

class Alarm(object):
    """An alarm is used to keep track of changing parameters in the system.
    Each one belongs to a specific group of related alarms, has certain priority
    and a text message (with str.format-compatible placeholders) for active
    and inactive state."""

    instances = defaultdict(list)

    def __init__(self, group, priority, on_message, off_message):
        self.priority = priority
        self.group = group
        self.on_message = on_message
        self.off_message = off_message

        self.active = False
        self.params = ()
        self.sent = True

        Alarm.instances[self.group].append(self)

    def update(self, active, *args):
        """Sets the alarm state to active or inactive;
        optional *args will be formatted into the message"""
        if self.active != active or self.params != args:
            self.active = active
            self.params = args
            self.sent = False

    def activate(self, *args):
        self.update(True, *args)

    def deactivate(self, *args):
        self.update(False, *args)

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
        return msg.format(*self.params)


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


