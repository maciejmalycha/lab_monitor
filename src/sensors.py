import paramiko
from iloresponse import ILOResponse
import time

class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=user, password=password)

    def show(self, component):
        cmd = "show "+component
        stdin,stdout,stderr = self.ssh.exec_command(cmd)
        output = stdout.readlines()
        return ILOResponse(output)

    def server_status(self):
        pass

    def power_use(self):
        response = self.show("/system1")
        return response.get("oemhp_PresentPower")

    def power_units(self):
        pass

    def temp_sensors(self):
        temp = {}
        sensors = ["/system1/sensor%u"%i for i in range(3,10)]

        for component in sensors:   
            response = self.show(component)
            temp[response.get("ElementName")] = response.get("CurrentReading")
            time.sleep(0.1) # otherwise it crashes

        return temp

