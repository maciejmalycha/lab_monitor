import server as s
import sensors
import database

def run(size):
    lab = s.Laboratory()
    sensors_dao = database.SensorsDAO()
    servers_dao = database.ServersDAO()

    for rackid in range(size):
        rack = s.Rack(rackid)
        lab.add_rack(rack)
        serv_list = servers_dao.server_list(rackid)
        for serv in serv_list:
            rack.add_server(s.Server(serv['addr'], s.ESXiHypervisor(serv['hypervisor']), sensors.SSHiLoSensors(serv['addr']), sensors_dao))

    return lab
