#!/usr/bin/env python

from collections import defaultdict
import datetime
import time

import yaml

from database import *
from server import *
import notifications as n


class Watchdog:
    def __init__(self, config='../watchdog.yaml'):
        with open(config) as cf:
            self.config = yaml.load(cf)

        self.notifier = n.HangoutNotification()
        self.sensors_dao = SensorsDAO()

        self.problems = []
        self.racks = [RackWatchdog(self, i) for i in range(7)]

    def check():
        self.problems = []
        for rack in self.racks:
            rack.check()
            self.problems.extend(rack.problems)

        merge_problems(self.problems, self.wd.config['thresholds']['lab'])

        for problem in self.problems:
            if isinstance(problem, n.LabShutdownSignal):
                pass # shut it down
            if isinstance(problem, n.RackShutdownSignal):
                pass # shut it down
            if isinstance(problem, n.ServerShutdownSignal):
                pass # shut it down

            self.notifier.send_notification(problem)


class RackWatchdog:
    def __init__(self, watchdog, rack_id):
        self.wd = watchdog
        self.rack_id = rack_id
        self.problems = []

        self.servers = [ServerWatchdog(self.wd, serv['addr']) \
                  for serv in self.wd.servers_dao.server_list()]

    def check():
        self.problems = []
        for server in self.servers:
            server.check()
            self.problems.extend(server.problems)

        merge_problems(self.problems, self.wd.config['thresholds']['rack']*len(self.servers))


class ServerWatchdog:
    def __init__(self, watchdog, server, last_timestamp=time.time()):
        self.wd = watchdog
        self.server = server
        self.last_timestamp = last_timestamp
        # in order to keep up with the data, every time check() is called
        # it will load and analyze all records newer than last timestamp.
        # after that, this variable is updated.
        self.problems = []

    def check(self):
        self.problems = []

        temperature = self.wd.sensors_dao.get_temperature(self.server['addr'],
                              datetime.fromtimestamp(self.last_timestamp))
        for sensor in self.wd.config['temperature']:
            readings = temperature[sensor['sensor']]
            for timestamp, value in readings:
                if value>sensor['critical']:
                    self.problems.append(n.ServerTemperatureShutdownSignal(server, value))
                elif value>sensor['high_warning']:
                    self.problems.append(n.ServerTemperatureRaiseSignal(server, value))
                elif value<sensor['low_warning']:
                    self.problems.append(n.ServerTemperatureDropSignal(server, value))

        # same thing with other parameters

def merge_problems(problems, threshold):
    categories = defaultdict(list)
    merged = []
    for problem in problems:
        categories[problem.__class__].append(problem)

    for ctg, listed in categories.iteritems():
        if len(listed)>=threshold and hasattr(ctg, 'PARENT'):
            merged.append(getattr(n, ctg.PARENT)(*listed))
        else:
            merged.extend(listed)

    problems[:] = merged

if __name__=='__main__':
    w = Watchdog()
