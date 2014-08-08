#!/usr/bin/env python

import atexit
import logging, logging.handlers

import redis

from config import config
import construct_lab
import database
import minuteworker
import notifications
import procutils

class Monitor(minuteworker.MinuteWorker):

    logger_name = 'lab_monitor.monitor.Monitor'

    def start(self, lab):
        self.lab = lab
        if not self.lab.servers:
            self.log.info("Nothing to monitor")
            return
        self.main_loop()

    def check_server(self, server):
        self.log.info("Checking server %s", server.addr)
        server.check_status()
        server.notify_alarms()
        server.store_status()

    def tasks(self):
        return [(self.check_server, (server,)) for server in self.lab.servers.itervalues()]

if __name__ == '__main__':
    baselog = logging.getLogger('lab_monitor')
    baselog.setLevel(logging.INFO)

    format = logging.Formatter("%(asctime)s  %(levelname)-8s %(name)-36s %(message)s", "%H:%M:%S")

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(format)
    baselog.addHandler(ch)

    rfh = logging.handlers.TimedRotatingFileHandler('../logs/monitor', 'midnight')
    rfh.setLevel(logging.INFO)
    rfh.setFormatter(format)
    baselog.addHandler(rfh)
    
    red = redis.StrictRedis(**config['redis'])

    def cleanup():
        baselog.info('Terminating')
        red.delete('lab_monitor.monitor_pid')
        red.delete('lab_monitor.last_state')
    atexit.register(cleanup)

    # a monitor registers its process id to redis,
    # if another instance is running right now,
    # interrupt it and wait until it finishes
    pid = red.get('lab_monitor.monitor_pid')
    if pid is not None:
        baselog.info('Waiting for process to terminate')
        procutils.kill_wait(pid)


    red.set('lab_monitor.monitor_pid', procutils.getpid())

    servers_dao = database.ServersDAO(config['database'])
    sensors_dao = database.SensorsDAO(config['database'])

    monitor_opts = {}
    monitor_opts['delay'] = config['alarm_delay']
    monitor_opts['shutdown_timeout'] = config['shutdown_timeout']
    monitor_opts['temperature'] = config['temperature']
    monitor_opts['engine'] = notifications.Hangouts(**config['xmpp'])


    def stateupd(state):
        red.publish('lab_monitor.state', state)
        red.set('lab_monitor.last_state', state)

    stateupd('starting')
    lab = construct_lab.run(config['num_racks'], servers_dao, sensors_dao, True, monitor_opts)
    
    mon = Monitor()
    mon.state_updater = stateupd
    mon.start(lab)
