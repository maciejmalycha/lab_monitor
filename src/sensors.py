import logging
import re

import paramiko
import gevent, gevent.monkey

paramiko.Transport._preferred_ciphers = ( 'aes128-cbc', '3des-cbc' )
paramiko.Transport._preferred_macs = ( 'hmac-md5', 'hmac-sha1' )
paramiko.Transport._preferred_keys = ( 'ssh-rsa', 'ssh-dss' )
paramiko.Transport._preferred_compression = ( 'none' )

gevent.monkey.patch_all()


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

        self.log = logging.getLogger('lab_monitor.sensors.SSHiLoSensors')
        self.log.info("Initializing")

        self.ssh = ILoSSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()
        self.detect_components()
    
    def connect(self):
        """Establishes connection with the iLo server"""
        self.log.info("Connecting to the iLo server at %s", self.host)
        self.ssh.connect(self.host, username=self.user, password=self.password)

    def disconnect(self):
        """Disconnects from the iLo server"""
        self.log.info("Disconnecting from the iLo server")
        self.ssh.close()

    def detect_components(self):
        """Loads all the power supplies and temperature sensors that will be monitored"""
        self.log.info("Detecting components")
        system = self.show("/system1", False)

        # I use list(set(...)) to remove duplicates, because they are there in the output
        self.sensors = list(set("/system1/{0}".format(a) for a in re.findall("    (sensor\d)", system)))
        self.power_supplies = list(set("/system1/{0}".format(a) for a in re.findall("    (powersupply\d)", system)))

        self.log.info("Found %u temperature sensors and %u power supplies", len(self.sensors), len(self.power_supplies))

    def show(self, component, autoparse=True, original=False):
        """Executes `show` command on the remote server and parses the output as a dictionary"""

        cmd = "show {0}".format(component)

        self.log.debug("Executing `%s` on %s", cmd, self.host)

        success = False
        while not success:
            try:
                stdin,stdout,stderr = self.ssh.exec_command(cmd)
                success = True
            except paramiko.SSHException as e:
                self.log.warning("Command failed (%s), reconnecting", e)
                self.disconnect()
                self.connect()

        output = stdout.read()
        self.log.debug("Command successful, received %u bytes of output", len(output))

        gevent.sleep(0.01) # otherwise, if executed in a loop, the program throws paramiko.ssh_exception.SSHException: Unable to open channel

        if autoparse:
            if original:
                return dict(re.findall("    (\w+)=([^\r]+)", output)), output
            else:
                return dict(re.findall("    (\w+)=([^\r]+)", output))
        else:
            return output

    def server_status(self):
        """Checks server status"""
        self.log.info("Checking status")

        response = self.show("/system1")
        try:
            return response['enabledstate']=="enabled"
        except KeyError:
            self.log.warning("Cannot find 'enabledstate', returning False")
            return False

    def power_use(self):
        """Returns power usage"""
        self.log.info("Checking power usage")

        response = self.show("/system1")

        data = {}
        for key,ilo_key in [('present','oemhp_PresentPower'), ('avg','oemhp_AveragePower'), ('min','oemhp_MinPower'), ('max','oemhp_MaxPower')]:
            try:
                data[key] = int(response[ilo_key].split()[0])
            except (KeyError, ValueError):
                self.log.warning("Cannot parse data for %s", ilo_key)
                data[key] = None

        return data

    def power_units(self):
        """ Returns health states and operational statuses of all power supplies"""
        self.log.info("Checking power units")

        data = {}

        for component in self.power_supplies:
            response = self.show(component)
            try:
                data[response['ElementName']] = {
                    'operational': response.get('OperationalStatus'),
                    'health': response.get('HealthState')
                }
            except KeyError:
                self.log.warning("Cannot parse data for %s", component)

        return data

    def temp_sensors(self):
        """Returns current readings of all temperature sensors"""
        data = {}

        for component in self.sensors:
            response = self.show(component)
            try:
                if response['CurrentReading'] != 'N/A':
                    data[response['ElementName']] = int(response['CurrentReading'])
            except (KeyError, ValueError):
                self.log.warning("Cannot parse data for %s", component)

            
        return data
