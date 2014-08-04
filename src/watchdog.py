#!/usr/bin/env python

from collections import defaultdict
import datetime
import logging
import time

import yaml

from database import *
# from server import *
import notifications as n

class Watchdog:
    def __init__(self, config='../watchdog.yaml'):
        self.log = logging.getLogger("lab_monitor.watchdog")
        self.log.info("Initializing")

        with open(config) as cf:
            self.log.info("Reading configuration")
            self.config = yaml.load(cf)

        # self.notifier = HangoutNotification()
        self.sensors_dao = SensorsDAO()
        self.servers_dao = ServersDAO()

        self.problems = []
        self.log.info("Creating rack watchdogs")
        self.racks = [RackWatchdog(self, i) for i in range(7)]

    def check(self):
        self.problems = []
        for rack in self.racks:
            self.log.info("Checking rack #%u", rack.rack_id)
            rack.check()
            self.problems.extend(rack.problems)

        merge_problems(self.problems, self.config['thresholds']['lab'], self.log)

        for problem in self.problems:
            if isinstance(problem, n.LabShutdownSignal):
                self.log.info("Need to shutdown the whole lab", problem.rack_id)
                pass # shut it down
            if isinstance(problem, n.RackShutdownSignal):
                self.log.info("Need to shutdown rack #%u", problem.rack_id)
                pass # shut it down
            if isinstance(problem, n.ServerShutdownSignal):
                self.log.info("Need to shutdown %s", problem.server.hypervisor)
                #hyperv = ESXiHypervisor(problem.server.hypervisor)
                #hyperv.shutdown()

            self.log.info("Sending '%s'", problem)
            # self.notifier.send_notification(problem)


class RackWatchdog:
    def __init__(self, watchdog, rack_id):
        self.wd = watchdog
        self.rack_id = rack_id
        self.log = logging.getLogger('lab_monitor.watchdog')

        self.problems = []

        self.servers = [ServerWatchdog(self.wd, serv) \
                  for serv in self.wd.servers_dao.server_list(rack=self.rack_id)]

    def check(self):
        self.problems = []
        for server in self.servers:
            server.check()
            self.problems.extend(server.problems)

        merge_problems(self.problems, self.wd.config['thresholds']['rack']*len(self.servers), self.log)


class ServerWatchdog:
    def __init__(self, watchdog, server, last_timestamp=time.time()):
        self.wd = watchdog
        self.log = logging.getLogger('lab_monitor.watchdog')
        self.server = server

        # in order to keep up with the data, every time check() is called
        # it will load and analyze all records newer than last timestamp.
        # after that, this variable is updated.
        self.last_timestamp = last_timestamp

        # assume everything's OK
        self.status = True
        self.temperature = dict(s['sensor'], True for s in self.wd.config['temperature'])
        self.

        self.problems = []

    def add_problem(self, signal, *args, **kwargs):
        self.log.info('Creating %s signal for %s', signal, self.server['addr'])
        signal_class = getattr(n, "Server{0}Signal".format(signal))

        if signal.startswith('Temperature'):
            signal_class = n.ServerTemperatureSignalsFactory.create(signal_class, kwargs['sensor'])

        signal_args = (self.server,)+args
        signal_obj = signal_class(*signal_args)
        self.log.info('%s', signal_obj)
        self.problems.append(signal_obj)

    def set_timestamp(self, timestamp):
        self.last_timestamp = max(timestamp/1000, self.last_timestamp)

    def check(self):
        self.problems = []
        t = datetime.fromtimestamp(self.last_timestamp)

        self.log.info("Checking %s, last timestamp: %s", self.server['addr'], t)

        statuses = self.wd.sensors_dao.get_status(self.server['addr'], t)['status']
        power_units = self.wd.sensors_dao.get_power_units(self.server['addr'], t)
        temperature = self.wd.sensors_dao.get_temperature(self.server['addr'], t)
        
        
        self.log.info("Read %u status records", len(statuses))
        for timestamp, status in statuses:
            if not status and self.status:
                self.add_problem('CommunicationLost', last_reading) # TODO KYPBA
                self.status = False
            elif status and not self.status:
                self.add_problem('CommunicationRestored')
                self.status = True
            # else do nothing, because it either means that everything is OK
            # or that communication is lost, but the user had already been notified
            self.set_timestamp(timestamp)

        self.log.info("Read %u power units records", len(power_units))
        for power_supply, data in power_units.iteritems():
            for timestamp, value in data:
                if not value and self.power_units.get(power_supply, True):
                    self.power_units[power_supply] = False
                    if power_supply == 'Power Supply 1':
                        self.add_problem('UPSPowerLoss')
                    elif power_supply == 'Power Supply 2':
                        self.add_problem('GridPowerLoss')
                    else:
                        self.add_problem('PowerLoss', power_supply)
                elif value and not self.power_units.get(power_supply, True):
                    self.power_units[power_supply] = True
                    self.add_problem('PowerRestored')
            self.set_timestamp(timestamp)

        # what about power_usage scope?

        for s in self.wd.config['temperature']:
            sensor = s['sensor']
            readings = temperature[sensor]
            self.log.info("Read %u temperature records for %s", len(readings), sensor)
            for timestamp, value in readings:
                if value>sensor['critical']:
                    self.add_problem('TemperatureShutdown', value, sensor=sensor)
                elif value>sensor['warning'] and self.temperature[sensor]:
                    self.add_problem('TemperatureRaise', value, sensor=sensor)
                    self.temperature[sensor] = False
                elif value<sensor['warning'] and not self.temperature[sensor]:
                    self.add_problem('TemperatureDrop', value, sensor=sensor)
                    self.temperature[sensor] = True

                self.set_timestamp(timestamp)

def merge_problems(problems, threshold, log):
    """Converts threshold problems of the same type
    to one parent problem (server -> rack, rack -> lab).
    Modifies the original problems list."""
    categories = defaultdict(list)
    merged = []
    for problem in problems:
        categories[problem.__class__].append(problem)

    for ctg, listed in categories.iteritems():
        if len(listed)>=threshold and hasattr(ctg, 'PARENT'):
            log.info("Merging %u %ss into one %s", len(listed), ctg.__name__, ctg.PARENT)
            merged.append(getattr(n, ctg.PARENT)(listed))
        else:
            merged.extend(listed)

    problems[:] = merged


logging.basicConfig(level=logging.INFO)
w = Watchdog()