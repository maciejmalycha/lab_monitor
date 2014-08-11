import server as s
import sensors
import alarms

def run(size, servers_dao, sensors_dao, monitor=False, monitor_opts=None):
    lab = s.Laboratory()

    for rackid in range(size):
        rack = s.Rack(rackid)
        lab.add_rack(rack)

        serv_list = servers_dao.server_list(rack.id)
        for serv in serv_list:
            hyperv = s.ESXiHypervisor(serv['hypervisor']) if serv['hypervisor'] else None
            sensors_inst = sensors.SSHiLoSensors(serv['addr']) if monitor else None

            server = s.Server(serv['addr'], hyperv, sensors_inst, sensors_dao, serv)
            rack.add_server(server)

    if monitor:
        create_alarms(lab, **monitor_opts)

    return lab

def create_alarms(lab, engine, delay, temperature, shutdown_timeout):
    # Not quite flexible, but I don't know how flexible should it be

    lab_ups = alarms.UPSLabPowerAlarm(None, lab, engine, delay)
    lab_grid = alarms.GridLabPowerAlarm(None, lab, engine, delay)
    lab_temp = alarms.LabTemperatureAlarm(None, lab, engine, delay, number=shutdown_timeout)

    for rack in lab.racks:
        rack_ups = alarms.UPSRackPowerAlarm(lab_ups, rack, engine, delay, rack=rack.id+1)
        rack_grid = alarms.GridRackPowerAlarm(lab_grid, rack, engine, delay, rack=rack.id+1)
        rack_temp = alarms.RackTemperatureAlarm(lab_temp, rack, engine, delay, rack=rack.id+1, number=shutdown_timeout)

        for serv in rack.servers:
            serv_conn = alarms.ConnectionAlarm(None, serv, engine, delay, server=serv.addr, threshold=5)
            serv_ups = alarms.UPSServerPowerAlarm(None, serv, engine, delay, server=serv.addr)
            serv_grid = alarms.GridServerPowerAlarm(None, serv, engine, delay, server=serv.addr)

            for s in temperature:
                sensor = s['sensor']
                warning = s['warning']
                critical = s['critical']
                temp = alarms.TemperatureAlarm(None, serv, engine, delay, server=serv.addr, sensor=sensor, threshold=warning)
                shutd = alarms.TemperatureShutdownAlarm(rack_temp, serv, engine, delay, server=serv.addr, sensor=sensor, threshold=critical, number=shutdown_timeout)
