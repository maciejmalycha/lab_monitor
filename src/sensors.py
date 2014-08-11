import logging
import re
import time
import string

import paramiko

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


class HostUnreachableException(IOError):
    pass


class SSHiLoSensors:

    def __init__(self, host="pl-byd-esxi13-ilo", user="Administrator", password="ChangeMe"):
        self.host = host
        self.user = user
        self.password = password
        self.sensors = []
        self.power_supplies = []
        self.redetect = True

        self.log = logging.getLogger('lab_monitor.sensors.SSHiLoSensors')
        self.log.info("Initializing")

        self.ssh = ILoSSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()

    def connect(self):
        """Establishes connection with the iLo server"""
        self.log.info("Connecting to the iLo server at %s", self.host)
        try:
            self.ssh.connect(self.host, username=self.user, password=self.password)
            return True
        except IOError as e:
            self.log.exception("Cannot connect to %s", self.host)

    def disconnect(self):
        """Disconnects from the iLo server"""
        self.log.info("Disconnecting from the iLo server")
        self.ssh.close()

    def detect_components(self):
        """Loads all the power supplies and temperature sensors that will be monitored"""
        self.log.info("Detecting components")

        try:
            system = self.show("/system1", False)
        except IOError as e:
            self.sensors = []
            self.power_supplies = []
            self.redetect = True

        # I use list(set(...)) to remove duplicates, because they are there in the output
        self.sensors = list(set("/system1/{0}".format(a) for a in re.findall("    (sensor\d)", system)))
        self.power_supplies = list(set("/system1/{0}".format(a) for a in re.findall("    (powersupply\d)", system)))

        self.redetect = False
        self.log.info("Found %u temperature sensors and %u power supplies", len(self.sensors), len(self.power_supplies))

    def show(self, component, autoparse=True, original=False):
        """Executes `show component` command on the remote server.
        If autoparse is set to True (by default it is), the output is be parsed as a dictionary.
        If original is set to True, unparsed output is also returned as the 2nd element of a tuple"""

        cmd = "show {0}".format(component)

        self.log.debug("Executing `%s` on %s", cmd, self.host)

        success = False
        for _ in range(3):
            try:
                stdin,stdout,stderr = self.ssh.exec_command(cmd)
                success = True
                break
            except paramiko.SSHException as e:
                self.log.warning("Command failed (%s), reconnecting", e)
                self.disconnect()
                self.connect()
            except AttributeError as e:
                # not even connected
                self.connect()

        if not success:
            self.log.error("Reconnection failed 3 times")
            raise HostUnreachableException()

        output = stdout.read()

        try:
            output = output.decode('utf-8')
        except UnicodeDecodeError:
            self.log.warning("Unicode error")

        output = ''.join(ch if ch in string.printable else "\\0x%02X"%ord(ch) for ch in output)

        self.log.debug("Command successful, received %u bytes of output:", len(output))
        self.log.debug("%s", output)

        time.sleep(0.01) # otherwise, if executed in a loop, the program throws paramiko.ssh_exception.SSHException: Unable to open channel

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

        response, original = self.show("/system1", original=True)
        try:
            enabled = response['enabledstate']=="enabled"
        except KeyError:
            self.log.warning("Cannot find 'enabledstate' in response from %s, returning False. Original output:\n%s", self.host, original)
            return False

        if enabled and self.redetect:
            self.detect_components()

        return enabled

    def power_use(self):
        """Returns power usage"""
        self.log.info("Checking power usage")

        response, original = self.show("/system1", original=True)

        data = {}
        ilo_keys = [
            ('present', 'oemhp_PresentPower'),
            ('average', 'oemhp_AveragePower'),
            ('minimum', 'oemhp_MinPower'),
            ('maximum', 'oemhp_MaxPower')
        ]
        for key, ilo_key in ilo_keys:
            try:
                data[key] = int(response[ilo_key].split()[0])
            except KeyError:
                self.log.warning("Power usage row %s not found at %s. Original output:\n%s", ilo_key, self.host, original)
            except (IndexError, ValueError):
                self.log.warning("Cannot parse data for %s at %s (%s)", ilo_key, self.host, response[ilo_key])
                data[key] = None

        return data

    def power_units(self):
        """ Returns health states and operational statuses of all power supplies"""
        self.log.info("Checking power units")

        data = {}

        for component in self.power_supplies:
            response, original = self.show(component, original=True)
            try:
                data[response['ElementName']] = {
                    'operational': response.get('OperationalStatus')=='Ok',
                    'health': response.get('HealthState')=='Ok'
                }
            except KeyError:
                self.log.warning("Cannot parse data for %s at %s. Original output:\n%s", component, self.host, original)

        return data

    def temp_sensors(self):
        """Returns current readings of all temperature sensors"""
        self.log.info("Checking temperature")
        data = {}

        for component in self.sensors:
            response, original = self.show(component, original=True)
            try:
                if response['CurrentReading'] != 'N/A':
                    data[response['ElementName']] = int(response['CurrentReading'])
                else:
                    self.log.debug("Reading for %s is N/A", component)
            except KeyError:
                self.log.warning("Cannot parse data for %s at %s. Original output:\n", component, self.host, original)
            except ValueError:
                self.log.warning("Cannot parse data for %s at %s (%s)", component, self.host, response['CurrentReading'])

        return data
