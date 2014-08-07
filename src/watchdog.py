#!/usr/bin/env python

from collections import defaultdict
import datetime
import logging
import time

import yaml

from minuteworker import MinuteWorker
from database import *
import notifications as n

class Watchdog(MinuteWorker):
    use_gevent = False
    logger_name = 'lab_monitor.watchdog'
    interval = 10

    def __init__(self, config='../watchdog.yaml'):
        super(Watchdog, self).__init__()

        with open(config) as cf:
            self.log.info("Reading configuration")
            self.config = yaml.load(cf)

        self.notifier = n.HangoutNotification(**self.config['xmpp'])
        self.sensors_dao = SensorsDAO()
        self.servers_dao = ServersDAO()

        self.problems = ProblemDict()
        self.log.info("Creating rack watchdogs")
        self.racks = [RackWatchdog(self, i) for i in range(7)]

    def tasks(self):
        return [(self.check, ())]

    def check(self):
        self.problems.clear()
        for rack in self.racks:
            self.log.info("Checking rack #%u", rack.rack_id)
            rack.check()
            self.problems.extend(rack.problems)

        self.problems.merge(self.config['thresholds']['lab'], self.log)

        for problem in list(self.problems):
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

            #self.log.warning("%s", problem)
            self.notifier.send_notification(problem)


class RackWatchdog(object):
    def __init__(self, watchdog, rack_id):
        self.wd = watchdog
        self.rack_id = rack_id
        self.log = logging.getLogger('lab_monitor.watchdog')

        self.problems = ProblemDict()

        self.servers = [ServerWatchdog(self.wd, serv) \
                  for serv in self.wd.servers_dao.server_list(rack=self.rack_id)]

    def check(self):
        self.problems.clear()
        for server in self.servers:
            server.check()
            self.problems.extend(server.problems)

        self.problems.merge(self.wd.config['thresholds']['rack']*len(self.servers), self.log)


class ServerWatchdog(object):
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
        self.temperature = dict((s['sensor'], True) for s in self.wd.config['temperature'])
        self.power_units = {'Power Supply 1': True, 'Power Supply 2': True}

        self.problems = ProblemDict()

    def add_problem(self, signal, *args):
        self.log.info('Creating %s signal for %s', signal, self.server['addr'])

        signal_class = getattr(n, "Server{0}Signal".format(signal))
        signal_args = (self.server,)+args
        signal_obj = signal_class(*signal_args)

        self.problems[signal_class].append(signal_obj)

    def set_timestamp(self, timestamp):
        # filtering by date/time uses SQL `between` (non-strict
        # inequalities) so next time the last record will be
        # also selected from the database; hence +1
        self.last_timestamp = max((timestamp+1)/1000, self.last_timestamp)

    def check(self):
        self.problems.clear()
        t = datetime.fromtimestamp(self.last_timestamp)

        self.log.info("Checking %s, last timestamp: %s", self.server['addr'], t)

        statuses = self.wd.sensors_dao.get_status(self.server['addr'], t)['status']
        power_units = self.wd.sensors_dao.get_power_units(self.server['addr'], t)
        temperature = self.wd.sensors_dao.get_temperature(self.server['addr'], t)
        
        
        self.log.info("Read %u status records", len(statuses))
        for timestamp, status in statuses:
            if not status and self.status:
                last_reading = 'N/A' if self.status is True else datetime.fromtimestamp(self.status)
                # self.status is initially set to True, so if it *is* True, it means
                # that this is the first reading and we don't know the date/time of last reading
                self.add_problem('CommunicationLost', last_reading)
                self.status = False
            elif status and not self.status:
                self.add_problem('CommunicationRestored')
                self.status = True
            elif status and self.status:
                self.status = timestamp/1000
            # else do nothing, because it means that communication
            # is lost, but the user had already been notified
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
                if value >= s['critical']:
                    self.add_problem('TemperatureShutdown', sensor, value)
                elif value >= s['warning'] and self.temperature[sensor]:
                    self.add_problem('TemperatureRaise', sensor, value)
                    self.temperature[sensor] = False
                elif value < s['warning'] and not self.temperature[sensor]:
                    self.add_problem('TemperatureDrop', sensor, value)
                    self.temperature[sensor] = True

                self.set_timestamp(timestamp)


class ProblemDict(defaultdict):
    def __init__(self):
        super(ProblemDict, self).__init__(list)

    def extend(self, other):
        for key, val in other.iteritems():
            self[key].extend(val)

    def __iter__(self):
        for key, val in self.iteritems():
            for item in val:
                yield item

    def merge(self, threshold, log):
        """Converts threshold problems of the same type
        to one parent problem (server -> rack, rack -> lab).
        Modifies the original problems dict."""

        for cl, listed in self.iteritems():
            if len(listed)>=threshold and hasattr(cl, 'PARENT'):
                log.info("Merging %u %ss into one %s", len(listed), cl.__name__, cl.PARENT)

                mclass = getattr(n, cl.PARENT)
                merged = mclass(listed)
                self[mclass].append(merged)
                del self[cl]

if __name__ == '__main__':
    logging.basicConfig()
    w = Watchdog('../watchdog.topsecret.yaml')
    w.start()