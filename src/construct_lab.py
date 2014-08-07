import server as s
import sensors
import database

def run(size):
    lab = s.Laboratory()

    for rackid in range(size):
        lab.add_rack(s.Rack(rackid))

    for rack in lab.racks:
        serv_list = database.ServersDAO().server_list(rack.id)
        for serv in serv_list:
            rack.add_server(s.Server(serv['addr'], s.ESXiHypervisor(serv['hypervisor']), sensors.SSHiLoSensors(serv['addr']), database.SensorsDAO()))

#czy to wszystko?
