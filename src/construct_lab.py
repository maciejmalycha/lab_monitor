import server as s
import sensors
import database

def run(size):
    lab = s.Laboratory()
    sensors_dao = database.SensorsDAO()
    servers_dao = database.ServersDAO()

    for rackid in range(size):
        lab.add_rack(s.Rack(rackid))

    for rack in lab.racks:
        serv_list = servers_dao.server_list(rack.id)
        for serv in serv_list:
            rack.add_server(s.Server(serv['addr'], s.ESXiHypervisor(serv['hypervisor']), sensors.SSHiLoSensors(serv['addr']), sensors_dao))

    return lab
