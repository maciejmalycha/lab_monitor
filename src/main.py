#!/usr/bin/env python

import logging

import frontend
import server
import database

class LabMonitor:
    def __init__(self):
        baselog = logging.getLogger('lab_monitor')
        baselog.setLevel(logging.INFO)

        format = logging.Formatter("%(asctime)s  %(levelname)-8s %(name)-36s %(message)s", "%H:%M:%S")

        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        ch.setFormatter(format)
        baselog.addHandler(ch)

        rfh = logging.handlers.TimedRotatingFileHandler('../logs/lab_monitor', 'midnight')
        rfh.setLevel(logging.INFO)
        rfh.setFormatter(format)
        baselog.addHandler(rfh)

        self.lab = None
        self.fe = None

    def set_lab(self, lab):
        self.lab = lab

    def set_frontend(self, frontend):
        self.fe = frontend
        self.fe.servers_dao = self.servers_dao
        self.fe.sensors_dao = self.sensors_dao
        self.fe.controller_start = self.controller_start
        self.fe.controller_stop = self.controller_stop
        self.fe.controller_restart = self.controller_restart
        self.fe.controller_status = self.controller_status
        self.fe.servers_changed = self.servers_changed
        self.fe.stream = None
        self.fe.lab = self.lab

    def controller_start(self):
        print "controller start"

    def controller_stop(self):
        print "controller stop"

    def controller_restart(self):
        self.controller_stop()
        self.controller_start()

    def controller_status(self):
        return "Freaking awesome"

    def servers_changed(self):
        print "Gotta recreate the lab"

    def start(self):
        self.fe.run(host='0.0.0.0')


if __name__ == '__main__':
    lm = LabMonitor()
    lm.sensors_dao = database.SensorsDAO()
    lm.servers_dao = database.ServersDAO()
    lm.set_lab(server.Laboratory())
    lm.set_frontend(frontend.app)
    lm.start()
