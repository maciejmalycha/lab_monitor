import paramiko
from iloresponse import ILoResponse
import time

paramiko.Transport._preferred_ciphers = ( 'aes128-cbc', '3des-cbc' )
paramiko.Transport._preferred_macs = ( 'hmac-md5', 'hmac-sha1' )
#paramiko.Transport._preferred_kex = ( 'diffie-hellman-group1-sha1' )
# this line causes Incompatible ssh peer exception, even though the KEX looks correct
paramiko.Transport._preferred_keys = ( 'ssh-rsa', 'ssh-dss' )
paramiko.Transport._preferred_compression = ( 'none' )


class ILoSSHClient(paramiko.SSHClient):
    def _auth(self, username, password, *args, **kwargs):
        if password is not None:
            self._transport.auth_password(username, password)
            return
        raise paramiko.ssh_exception.SSHException("No authentication methods available")


class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        self.ssh = ILoSSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=user, password=password)

    def show(self, component):
        cmd = "show "+component
        stdin,stdout,stderr = self.ssh.exec_command(cmd)
        output = stdout.readlines()
        return ILoResponse(output)

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

if __name__=='__main__':
    s = SSHiLoSensors()
    print s.power_use()