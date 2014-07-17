import paramiko
import time
import re

paramiko.Transport._preferred_ciphers = ( 'aes128-cbc', '3des-cbc' )
paramiko.Transport._preferred_macs = ( 'hmac-md5', 'hmac-sha1' )
paramiko.Transport._preferred_keys = ( 'ssh-rsa', 'ssh-dss' )
paramiko.Transport._preferred_compression = ( 'none' )


def first2int(val):
    a,b = val.split(' ')
    return int(a)

class ILoSSHClient(paramiko.SSHClient):
    def _auth(self, username, password, *args, **kwargs):
        if password is not None:
            self._transport.auth_password(username, password)
            return
        raise paramiko.ssh_exception.SSHException("No authentication methods available")


class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        """Establishes connection with the iLo server"""
        self.ssh = ILoSSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=user, password=password)

    def show(self, component):
        """Executes `show` command on the remote server and parses the output as a dictionary"""
        cmd = "show "+component
        stdin,stdout,stderr = self.ssh.exec_command(cmd)
        output = stdout.read()
        time.sleep(0.01) # otherwise, if executed in a loop, the program throws paramiko.ssh_exception.SSHException: Unable to open channel
        return dict(re.findall("    (\w+)=([^\r]+)", output))

    def server_status(self):
        """Checks server status"""
        response = self.show("/system1")
        return response['enabledstate']=="enabled"

    def power_use(self):
        """Returns power usage"""
        response = self.show("/system1")
        return {
            'present': first2int(response['oemhp_PresentPower']),
            'avg': first2int(response['oemhp_AveragePower']),
            'min': first2int(response['oemhp_MinPower']),
            'max': first2int(response['oemhp_MaxPower'])
        }

    def power_units(self):
        """ Returns health states and operational statuses of all power supplies"""
        data = {}
        units = ["/system1/powersupply%u"%i for i in range(1,3)]

        for component in units:
            response = self.show(component)
            data[response['ElementName']] = {
                'operational': response['OperationalStatus'],
                'health': response['HealthState']
            }

        return data

    def temp_sensors(self):
        """Returns current readings of all temperature sensors"""
        data = {}
        sensors = ["/system1/sensor%u"%i for i in range(3,10)]

        for component in sensors:
            response = self.show(component)
            data[response['ElementName']] = int(response['CurrentReading'])
            
        return data