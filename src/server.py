import logging
import time
import datetime

import paramiko

import database
import sensors as sensors_mod

class ESXiHypervisor:
    #initialazing - connecting to the ESXi server
    def __init__(self, hostname, username="root", password="ChangeMe"):
        self.addr = hostname

        self.log = logging.getLogger("lab_monitor.server.ESXiHypervisor")
        self.log.info("Connecting...")

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname, username=username, password=password)

    def check_vmwaretools(self, vmid):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/get.summary {0} | grep toolsVersionStatus | awk {{'print $3'}}".format(vmid))
        output = stdout.read().split()
        if output:
            output = filter(lambda c: c.isalpha(), output[0])
            if output == "guestToolsNotInstalled":
                return False
            elif output == "guestToolsCurrent" or output == "guestToolsNeedUpgrade":
                return True
        return False

    def get_status(self, vmid):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.getstate {0} | tail -1 | awk '{{print $2}}'".format(vmid))
        output = stdout.read().strip('\n')
        return (output == "on")

    def wait_for_shutdown(self, timeout, vmid, forced):
        #print "lets start a timer"
        start = time.time()
        elapsed = time.time()
        while (elapsed - start) < timeout:
            status = self.get_status(vmid)
            if status == False:
                return True
            elapsed = time.time()
            #print "Actual running time:", (elapsed - start)
            time.sleep(0.5)
        if forced:
            out = self.force_shutdown_vm(vmid)
            self.log.debug(out.read())
            return True
        else:
            self.log.error("Error occurred. Status didn't change after elapsed time.")
            return False


    #IDs of VMs are stored in an array, then we loop over IDs and get their statuses
    #If status is 'on', then we shutdown the VM and we add the ID to the list of IDs that are already shutted down by us
    def status(self):
        VMSL = {}
        #stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk '{print $1}'")
        """ Ok so basically I found an exception, where in column with Vmids were also other 'non-number' things, so I had to make an if statement to prevent such a things. This thing occured on pl-byd-esxi12 server"""
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk 'function isnum(x){return(x==x+0)}{if(isnum($1)) print $1}'")
        output = stdout.read().split()
        for i in output:
            vmid = i
            act_vm = self.get_status(vmid)
            VMSL[vmid] = act_vm
        return VMSL


    def shutdown(self, timeout=30):
        VMSL = self.status()
        VMidSL = VMSL.keys()
        AVMSL = []
        for vmid in VMidSL:
            if VMSL[vmid]:
                AVMSL.append(vmid)
        for i in AVMSL:
            if not self.check_vmwaretools(int(i)):
                self.log.warning("vmWareTools not installed on vm id=%s Can't perform shutdown", i)
            else:
                err = self.shutdown_vm(int(i))
                self.log.info("Shutting down VM: %s", i)
        start = time.time()
        elapsed = time.time()
        while (elapsed - start) < timeout and AVMSL:
            self.log.info("Active VMs: %s", AVMSL)
            for i in AVMSL:
                if self.get_status(int(i)) == False:
                    self.log.info("VMID down: %s", i)
                    AVMSL.remove(i)
            elapsed = time.time()
            time.sleep(0.5)
        if AVMSL:
            self.log.error("Shutdown failed. There are still working machines.")
            return False
        else:
            self.log.info("All done. Powering off")
            return True
        # self.ssh.exec_command("/sbin/shutdown.sh")
        # self.ssh.exec_command("/sbin/poweroff")

    def force_shutdown(self, timeout=30):
        VMSL = self.status()
        VMidSL = VMSL.keys()
        AVMSL = []
        for vmid in VMidSL:
            if VMSL[vmid]:
                AVMSL.append(vmid)
        for i in AVMSL:
            if not self.check_vmwaretools(int(i)):
                self.log.warning("vmWareTools not installed on vm id=%s  Performing force_shutdown()", i)
                out = self.force_shutdown_vm(int(i))
            else:
                err = self.shutdown_vm(int(i))
                self.log.info("Shutting down VM: %s", i)
        start = time.time()
        elapsed = time.time()
        while (elapsed - start) < timeout and AVMSL:
            self.log.info("Active VMs: %s", AVMSL)
            for i in AVMSL:
                if self.get_status(int(i)) == False:
                    self.log.info("VMID down: %s", i)
                    AVMSL.remove(i)
            elapsed = time.time()
            time.sleep(0.5)
        if AVMSL:
            self.log.info("Shutdown failed. There are still working machines. \nForcing shutdown...")
            for i in AVMSL:
                out = self.force_shutdown_vm(int(i))
                out.read()
            self.log.info("All done. Powering off")
            return True
        #self.ssh.exec_command("/sbin/shutdown.sh")
        #self.ssh.exec_command("/sbin/poweroff")

    def force_shutdown_vm(self, VM_id):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.off {0}".format(VM_id))
        return stdout.read()

    def shutdown_vm(self, VM_id):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.shutdown {0}".format(VM_id))
        if stderr.read() != "":
            return False
        return True

    def execute_shutdown_vm(self, VM_id, timeout=0, forced=False):
        res = self.shutdown_vm(VM_id)
        if res == False:
            if forced:
                self.log.info("Forcing a shutdown vm id=%s", VM_id)
                out = self.force_shutdown_vm(VM_id)
                return out
            self.log.warning("Shutting down failed.")
            return False
        else:
            if timeout > 0:
                res = self.wait_for_shutdown(timeout, VM_id, forced)
                return False
            return True

class ESXiVirtualMachine:

    def __init__(self, vmid, hypervisor):
        self.id = vmid
        self.hypervisor = hypervisor

    #Returning status of a VM
    def status(self):
        return self.hypervisor.get_status(self.id)

    #Shutting down a VM
    def shutdown(self):
        return self.hypervisor.shutdown_vm(self.id)

    #Force shutting down of a VM
    def force_shutdown(self):
        return self.hypervisor.force_shutdown_vm(self.id)


class Server:
    def __init__(self, addr, hypervisor, sensors, sensors_dao, record):
        self.addr = addr
        self.alarms = []
        self.hypervisor = hypervisor
        self.sensors = sensors
        self.sensors_dao = sensors_dao
        self.record = record
        self.rack = None
        self.server_status = None
        self.power_units = {
            'Power Supply 1': {'health': None, 'operational': None},
            'Power Supply 2': {'health': None, 'operational': None}
        }
        self.power_usage = {'present': None, 'average': None, 'minimum': None, 'maximum': None}
        self.last_reading = datetime.datetime.fromtimestamp(0)
        self.temperature = {}

    def register_alarm(self, alarm):
        self.alarms.append(alarm)

    def notify_alarms(self):
        for alarm in self.alarms:
            alarm.check()

    def add_reading(self, name, value):
        #TODO: Add reading to readings dictionary
        self.temperature[name] = value # ?

    def check_status(self):
        try:
            self.server_status = self.sensors.server_status()
            self.power_usage = self.sensors.power_use()
            self.power_units = self.sensors.power_units()
            self.temperature = self.sensors.temp_sensors()

        except sensors_mod.HostUnreachableException:
            # it has already been logged
            self.server_status = False

        if self.server_status:
            self.last_reading = datetime.datetime.now()

    def store_status(self):
        self.sensors_dao.store_server_status(self.addr, self.server_status)

        for unit, state in self.power_units.iteritems():
            if state['health'] is None and state['operational'] is None:
                # SSHiLoSensors would return bool. If those values are None,
                # it means data is not available, so we shouldn't store it
                continue
            self.sensors_dao.store_power_unit(self.addr, unit, **state)

        if self.server_status:
            # if server is down, you won't find anything interesting here
            self.sensors_dao.store_power_usage(self.addr, **self.power_usage)

            for sensor, reading in self.temperature.iteritems():
                self.sensors_dao.store_temperature(self.addr, sensor, reading)

    def shutdown(self, timeout=None):
        self.hypervisor.shutdown(timeout)

    def force_shutdown(self, timeout=None):
        self.hypervisor.force_shutdown(timeout)

    def __repr__(self):
        return "<Server {0}>".format(self.addr)


class Rack:
    def __init__(self, rack_id):
        self.id = rack_id
        self.servers = []
        self.alarms = []
        self.lab = None
        self.log = logging.getLogger("lab_monitor.server.Rack")
        self.log.info("Initialazing rack with id=%s", self.id)
        

    def add_server(self, server):
        server.rack = self

        self.lab.servers[server.addr] = server
        if server.hypervisor is not None:
            self.lab.hypervisors[server.hypervisor.addr] = server.hypervisor

        self.servers.append(server)

    def register_alarm(self, alarm):
        self.alarms.append(alarm)

    def status(self):
        if not self.servers:
            self.log.error("Not found")
        for server in self.servers:
            self.log.info("Getting status of %s", server.hypervisor.addr)
            self.log.info("%s", server.hypervisor.status())

    def shutdown(self, timeout=None):
        force_list = []
        for server in self.servers:
            self.log.info("Initialazing shutdown on %s", server.hypervisor.addr)
            err = server.hypervisor.shutdown(timeout)
            if err:
                self.log.info("Everything went OK")
            else:
                self.log.error("Something went wrong. Error occurred.\nAdding hypervisor to force_list")
                force_list.append(server.hypervisor)
        return force_list if force_list else None

    def force_shutdown(self, timeout=None):
        for server in self.servers:
            self.log.info("Initialazing shutdown on %s", server.hypervisor.addr)
            err = server.hypervisor.shutdown(timeout)
            if err:
                self.log.info("Everything went OK")
            else:
                self.log.error("Something went wrong. Error occurred.\nInitialazing force_shutdown")
                server.hypervisor.force_shutdown(timeout)

    def __repr__(self):
        return "<Rack #{0}>".format(self.id)


class Laboratory:
    def __init__(self):
        self.racks = []
        self.log = logging.getLogger("lab_monitor.server.Laboratory")
        self.log.info("Initialazing lab")

        self.alarms = []

        self.servers = {}
        self.hypervisors = {}

    def add_rack(self, rack):
        rack.lab = self

        self.racks.append(rack)

    def register_alarm(self, alarm):
        self.alarms.append(alarm)

    def status(self):
        for rack in self.racks:
            self.log.info("Getting status of rack %s", rack.id)
            rack.status()

    def shutdown(self, timeout=None):
        for rack in self.racks:
            self.log.info("Initialazing shutdown on rack: %s", rack.id)
            rack.shutdown(timeout)

    def force_shutdown(self, timeout=None):
        for rack in self.racks:
            self.log.info("Initialazing shutdown on rack: %s", rack.id)
            res = rack.shutdown(timeout)
            if res is not None:
                for hyp in res:
                    self.log.info("Shutdown failed. Forcing shutdown of a hypervisor: %s", hyp.addr)
                    hyp.force_shutdown(timeout)

    def __repr__(self):
        return "<Laboratory>"


