from datetime import datetime
import logging

import alarms
import database
#import sensors
import mock_sensors as sensors


class Server(object):
    def __init__(self, addr, hypervisor, rack, **kwargs):
        self.addr = addr
        self.hyperv_addr = hypervisor
        self.rack = rack

        self.sensors_dao = database.SensorsDAO()

        self.log = logging.getLogger('lab_monitor.server.Server')

        self.sensors = sensors.SSHiLoSensors(self.addr)
        #self.hypervisor = server.ESXiHypervisor(self.hyperv_addr)

        self.alarms = {}
        self.alarms['status'] = alarms.Alarm(
            'status', 1,
            "Connection with {server} lost. Last reading from {date}",
            "Connection with {server} restored",
            server=self.addr
        )
        self.alarms['ups_power'] = alarms.Alarm(
            'ups_power', 1,
            "Power loss in {server} detected. Suspected UPS failure",
            "UPS power in {server} restored",
            server=self.addr
        )
        self.alarms['grid_power'] = alarms.Alarm(
            'grid_power', 1,
            "Power loss in {server} detected. Suspected power grid failure",
            "Grid power in {server} restored",
            server=self.addr
        )
        self.create_temp_alarms({
            'Ambient Zone': (25, 30),
        })

    def create_temp_alarms(self, sensors):
        # the two following master alarms aren't meant to be sent
        # (hence 0 priority), but they are used to catch temperature raise
        # in the entire rack or laboratory (they're being watched by
        # a master alarm in the rack)
        self.alarms['temperature'] = alarms.MasterAlarm(
            'temperature', 0,
            "Temperature of {server} raised", "Temperature of {server} dropped",
            server=self.addr
        )
        self.alarms['shutdown_temperature'] = alarms.MasterAlarm(
            'temperature', 0,
            "Temperature of {server} raised. Shutting down.",
            "Temperature of {server} dropped. Aborting shutdown.",
            server=self.addr
        )

        # don't get confused, ['temperature'] and ['temperature_shutdown']
        # are master alarms, but in ['temp'] there's an alarm for each sensor
        self.alarms['temp'] = {}
        for sensor, (warning, shutdown) in sensors.iteritems():
            warn_alarm = alarms.TemperatureAlarm(1, warning, server=self.addr, sensor=sensor)
            shut_alarm = alarms.TemperatureAlarm(2, shutdown,
                "Temperature of {server} at {sensor} reached {reading} C. Shutting down.",
                "Temperature of {server} at {sensor} dropped to {reading} C. Aborting shutdown.",
                server=self.addr, sensor=sensor)

            self.alarms['temperature'].add_watched(warn_alarm)
            self.alarms['shutdown_temperature'].add_watched(shut_alarm)

            self.alarms['temp'][sensor] = [warn_alarm, shut_alarm]

    def check(self):
        try:
            server_status = self.sensors.server_status()
            self.sensors_dao.store_server_status(self.addr, server_status)
            if server_status:
                self.alarms['status'].deactivate(date=datetime.now())
            else:
                self.alarms['status'].activate()

            power_use = self.sensors.power_use()
            self.sensors_dao.store_power_usage(self.addr, power_use['present'], power_use['avg'], power_use['min'], power_use['max'])

            power_units = self.sensors.power_units()
            for power_supply, state in power_units.iteritems():
                self.sensors_dao.store_power_unit(self.addr, power_supply, state['operational'], state['health'])
                ok = state['operational'] and state['health']
                if power_supply == 'Power Supply 1':
                    self.alarms['ups_power'].update(not ok)
                elif power_supply == 'Power Supply 2':
                    self.alarms['grid_power'].update(not ok)

            temp_sensors = self.sensors.temp_sensors()
            for sensor, reading in temp_sensors.iteritems():
                self.sensors_dao.store_temperature(self.addr, sensor, reading)
                for alarm in self.alarms['temp'].get(sensor, []):
                    alarm.update(reading)
            self.alarms['temperature'].update()
            self.alarms['shutdown_temperature'].update()

            self.log.info("Finished checking %s", self.addr)

        except sensors.HostUnreachableException:
            # it has already been logged
            self.sensors_dao.store_server_status(self.addr, False)


class Rack(object):

    def __init__(self, rack_id):
        self.servers = [Server(**data) for data in database.ServersDAO().server_list(rack_id)]
        self.rack_id = rack_id

        self.master_alarms = {}
        self.master_alarms['status'] = alarms.MasterAlarm(
            'status', 2,
            "Connection with rack {rack} lost",
            "Connection with rack {rack} restored",
            rack=self.rack_id+1
        )
        self.master_alarms['ups_power'] = alarms.MasterAlarm(
            'ups_power', 2,
            "Power loss in rack {rack} detected. Suspected UPS failure",
            "UPS power in rack {rack} restored",
            rack=self.rack_id+1
        )
        self.master_alarms['grid_power'] = alarms.MasterAlarm(
            'grid_power', 2,
            "Power loss in rack {rack} detected. Suspected power grid failure",
            "Grid power in rack {rack} restored",
            rack=self.rack_id+1
        )
        self.master_alarms['temperature'] = alarms.MasterAlarm(
            'temperature', 3,
            "Temperature in rack {rack} raised",
            "Temperature in rack {rack} dropped",
            rack=self.rack_id+1
        )
        self.master_alarms['shutdown_temperature'] = alarms.MasterAlarm(
            'temperature', 4,
            "Temperature in rack {rack} raised. Shutting down.",
            "Temperature in rack {rack} dropped. Aborting shutdown.",
            rack=self.rack_id+1
        )

        for key, master in self.master_alarms.iteritems():
            for serv in self.servers:
                master.add_watched(serv.alarms[key])
            master.set_threshold(len(self.servers)*0.5)

    def check(self):
        for serv in self.servers:
            serv.check()

        for master in self.master_alarms.itervalues():
            master.update()


class Laboratory(object):

    def __init__(self):
        self.racks = [Rack(i) for i in range(7)]

        self.master_alarms = {}
        self.master_alarms['status'] = alarms.MasterAlarm(
            'status', 3,
            "Connection with laboratory lost",
            "Connection with laboratory restored"
        )
        self.master_alarms['ups_power'] = alarms.MasterAlarm(
            'ups_power', 3,
            "Power loss in laboratory detected. Suspected UPS failure",
            "UPS power in laboratory restored"
        )
        self.master_alarms['grid_power'] = alarms.MasterAlarm(
            'grid_power', 3,
            "Power loss in laboratory detected. Suspected power grid failure",
            "Grid power in laboratory restored"
        )
        self.master_alarms['temperature'] = alarms.MasterAlarm(
            'temperature', 4,
            "Temperature in laboratory raised",
            "Temperature in laboratory dropped",
        )
        self.master_alarms['shutdown_temperature'] = alarms.MasterAlarm(
            'temperature', 5,
            "Temperature in laboratory raised. Shutting down.",
            "Temperature in laboratory dropped. Aborting shutdown.",
        )

        for key, master in self.master_alarms.iteritems():
            for rack in self.racks:
                master.add_watched(rack.master_alarms[key])
            master.set_threshold(5)

    def check(self):
        for rack in self.racks:
            rack.check()

        for master in self.master_alarms.itervalues():
            master.update()

