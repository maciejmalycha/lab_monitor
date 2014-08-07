import server as s
import sensors
import database

def run(size):
	lab = s.Laboratory()
	lab_size = size	

	for rackid in range(lab_size):
		if database.ServersDAO().server_list(rackid):
			lab.add_rack(s.Rack(rackid))

	for rack in lab.racks:
		serv_list = database.ServersDAO().server_list(rack.id)
		for serv in serv_list:
			rack.add_server(s.Server(serv['addr'], s.ESXiHypervisor(serv['hypervisor']), sensors.SSHiLoSensors(serv['addr']), database.SensorsDAO()))
