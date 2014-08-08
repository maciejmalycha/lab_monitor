#!/usr/bin/env python

import atexit
import logging, logging.handlers
import sys
import subprocess

import redis

from config import config
import construct_lab
import database
import frontend
import procutils
import server
import sse

class LabMonitor:
    def __init__(self):
        self.lab = None
        self.labmaker = None
        self.fe = None
        self.red = None
        self.stream = None

    def set_redis(self, red):
        self.red = red
        self.stream = sse.EventStream(self.red, 'lab_monitor.state')

    def set_labmaker(self, labmaker):
        self.labmaker = labmaker
        self.lab = self.labmaker()

    def set_frontend(self, frontend):
        self.fe = frontend
        self.fe.servers_dao = self.servers_dao
        self.fe.sensors_dao = self.sensors_dao
        self.fe.monitor_start = self.monitor_start
        self.fe.monitor_stop = self.monitor_stop
        self.fe.monitor_restart = self.monitor_start
        # ^ in current implementation a monitor terminates existing process before proceeding 
        self.fe.monitor_status = self.monitor_status
        self.fe.servers_changed = self.servers_changed
        self.fe.stream = self.stream
        self.fe.lab = self.lab

    def monitor_start(self):
        subprocess.Popen([sys.executable, 'monitor.py'], close_fds=True)

    def monitor_stop(self):
        if self.monitor_status() != 'off':
            procutils.intrr(self.mpid())

    def monitor_status(self):
        if procutils.process_exists(self.mpid()):
            return self.red.get('lab_monitor.last_state') or "off"
        else:
            return "off"

    def mpid(self):
        return self.red.get('lab_monitor.monitor_pid')

    def servers_changed(self):
        if self.monitor_status() != "off":
            self.monitor_start()

        self.fe.lab = self.lab = self.labmaker()

    def start(self, debug=False):
        try:
            self.fe.run(host='0.0.0.0', debug=debug, use_reloader=False, threaded=True)
        except (KeyboardInterrupt, SystemExit):
            return


if __name__ == '__main__':

    print procutils.getpid()

    baselog = logging.getLogger('lab_monitor')
    baselog.setLevel(logging.INFO)

    format = logging.Formatter("%(asctime)s  %(levelname)-8s %(name)-36s %(message)s", "%H:%M:%S")

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(format)
    baselog.addHandler(ch)

    rfh = logging.handlers.TimedRotatingFileHandler('../logs/web', 'midnight')
    rfh.setLevel(logging.INFO)
    rfh.setFormatter(format)
    baselog.addHandler(rfh)

    servers_dao = database.ServersDAO(config['database'])
    sensors_dao = database.SensorsDAO(config['database'])
    labmaker = lambda: construct_lab.run(config['num_racks'], servers_dao, sensors_dao)

    red = redis.StrictRedis(**config['redis'])

    lm = LabMonitor()
    lm.sensors_dao = sensors_dao
    lm.servers_dao = servers_dao
    lm.set_labmaker(labmaker)
    lm.set_redis(red)
    lm.set_frontend(frontend.app)

    atexit.register(lm.monitor_stop)

    lm.start(debug=True)
