#!/usr/bin/env python

import datetime
import time

import yaml

from database import *
from server import *

class Watchdog:
    def __init__(self, config='../watchdog.yaml'):
        with open(config) as cf:
            self.config = yaml.load(cf)

        self.notifier = EmailNotification()
        self.sensors_dao = SensorsDAO()


class ServerWatchdog:
    def __init__(self, watchdog, last_timestamp=time.time()):
        self.wd = watchdog
        self.last_timestamp = last_timestamp

    def check(self):
        temperature = self.wd.sensors_dao.get_temperature(server['addr'],
                              datetime.fromtimestamp(self.last_timestamp))
        for sensor in self.wd.config['temperature']:
            readings = temperature[sensor['sensor']]
            for timestamp, value in readings:
                if value>sensor['critical']:
                    pass
                elif value>sensor['high_warning']:
                    pass
                elif value<sensor['low_warning']:
                    pass

if __name__=='__main__':
    w = Watchdog()
