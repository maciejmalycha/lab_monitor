import paramiko
import time
import re

paramiko.Transport._preferred_ciphers = ( 'aes128-cbc', '3des-cbc' )
paramiko.Transport._preferred_macs = ( 'hmac-md5', 'hmac-sha1' )
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
        self.host = host
        self.user = user
        self.password = password

        self.ssh = ILoSSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()
        self.detect_components()
    
    def connect(self):
        """Establishes connection with the iLo server"""
        self.ssh.connect(self.host, username=self.user, password=self.password)

    def disconnect(self):
        """Disconnects from the iLo server"""
        self.ssh.close()

    def detect_components(self):
        """Loads all the power supplies and temperature sensors that will be monitored"""
        system = self.show("/system1", False)

        self.sensors = ["/system1/%s"%a for a in re.findall("    (sensor\d)", system)]
        self.power_supplies = ["/system1/%s"%a for a in re.findall("    (powersupply\d)", system)]

    def show(self, component, autoparse=True):
        """Executes `show` command on the remote server and parses the output as a dictionary"""

        # it might have disconnected
        if not self.ssh.get_transport().is_authenticated():
            self.connect()

        cmd = "show "+component
        stdin,stdout,stderr = self.ssh.exec_command(cmd)
        output = stdout.read()
        time.sleep(0.01) # otherwise, if executed in a loop, the program throws paramiko.ssh_exception.SSHException: Unable to open channel

        if autoparse:
            return dict(re.findall("    (\w+)=([^\r]+)", output))
        else:
            return output

    def server_status(self):
        """Checks server status"""
        response = self.show("/system1")
        return response['enabledstate']=="enabled"

    def power_use(self):
        """Returns power usage"""
        response = self.show("/system1")
        return {
            'present': int(response['oemhp_PresentPower'].split()[0]),
            'avg': int(response['oemhp_AveragePower'].split()[0]),
            'min': int(response['oemhp_MinPower'].split()[0]),
            'max': int(response['oemhp_MaxPower'].split()[0])
        }

    def power_units(self):
        """ Returns health states and operational statuses of all power supplies"""
        data = {}

        for component in self.power_supplies:
            response = self.show(component)
            data[response['ElementName']] = {
                'operational': response['OperationalStatus'],
                'health': response['HealthState']
            }

        return data

    def temp_sensors(self):
        """Returns current readings of all temperature sensors"""
        data = {}

        for component in self.sensors:
            response = self.show(component)
            if response['CurrentReading'] != 'N/A':
                data[response['ElementName']] = int(response['CurrentReading'])
            
        return data
