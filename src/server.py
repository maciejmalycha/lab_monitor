import paramiko
import time
import logging, logging.handlers
import database
import xmpp

baselog = logging.getLogger('lab_monitor')
baselog.setLevel(logging.INFO)
format = logging.Formatter("%(asctime)s %(levelname)-8s %(name)-36s %(message)s", "%H:%M:%S")
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
ch.setFormatter(format)
baselog.addHandler(ch)

rfh = logging.handlers.TimedRotatingFileHandler('../lab_monitor/logs/lab_monitor', 'midnight')
rfh.setLevel(logging.INFO)
rfh.setFormatter(format)
baselog.addHandler(rfh)

class ESXiHypervisor:
    #initialazing - connecting to the ESXi server
    def __init__(self, hostname, username="root", password="ChangeMe"):
        self.addr = hostname

        self.log = logging.getLogger("lab_monitor.server.ESXiHypervisor")
        self.log.setLevel(logging.INFO)
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

    #Shutting down every working VM
    def shutdown(self, timeout):
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
               # err.read()
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

    def force_shutdown(self, timeout):
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
              #  err.read()
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
        return self.hESXiHypervisor.force_shutdown_vm(self.id)

class Rack:
    def __init__(self, rackid):
        self.id = rackid
        self.log = logging.getLogger("lab_monitor.server.Rack")
        self.log.setLevel(logging.INFO)
        self.log.info("Initialazing rack with id=%s", self.id)

    def get_hypervisors_from_db(self):
        print database.ServersDAO().server_list(self.id)
        return database.ServersDAO().hypervisor_list(self.id)
    
    def get_hypervisors_ready(self):
        return [ESXiHypervisor(hyperv['addr']) for hyperv in self.get_hypervisors_from_db()]
        
    def status(self):
        hyper_list = self.get_hypervisors_ready()
        if not hyper_list:
            self.log.error("Not found")
        for hypervisor in hyper_list:
            self.log.info("Getting status of %s", hypervisor.addr)
            self.log.info("%s", hypervisor.status())

    def shutdown(self, timeout):
        hyper_list = self.get_hypervisors_ready()
        force_list = []
        for hypervisor in hyper_list:
            self.log.info("Initialazing shutdown on %s", hypervisor.addr)
            err = hypervisor.shutdown(timeout)
            if err:
                self.log.info("Everything went OK")
            else:
                self.log.error("Something went wrong. Error occurred.\nAdding hypervisor to force_list")
                force_list.append(hypervisor)
        return force_list if force_list else None

    def force_shutdown(self, timeout):
        hyper_list = self.get_hypervisors_ready()
        for hypervisor in hyper_list:
            self.log.info("Initialazing shutdown on %s", hypervisor.addr)
            err = hypervisor.shutdown(timeout)
            if err:
                self.log.info("Everything went OK")
            else:
                self.log.error("Something went wrong. Error occurred.\nInitialazing force_shutdown")
                hypervisor.force_shutdown(timeout)

class Laboratory:
    def __init__(self):
        self.log = logging.getLogger("lab_monitor.server.Laboratory")
        self.log.setLevel(logging.INFO)
        self.log.info("Initialazing lab")

    def get_racks(self):
        return [Rack(rackid) for rackid in range(7)]

    def status(self):
        racks = self.get_racks()
        for rack in racks:
            self.log.info("Getting status of rack %s", rack.id)
            rack.status()

    def shutdown(self, timeout):
        racks = self.get_racks()
        for rack in racks:
            self.log.info("Initialazing shutdown on rack: %s", rack.id)
            rack.shutdown(timeout)

    def force_shutdown(self, timeout):
        racks = self.get_racks()
        for rack in racks:
            self.log.info("Initialazing shutdown on rack: %s", rack.id)
            res = rack.shutdown(timeout)
            if res is not None:
                for hyp in res:
                    self.log.info("Shutdown failed. Forcing shutdown of a hypervisor: %s", hyp.addr)
                    hyp.force_shutdown(timeout)

class HangoutNotification():
    def __init__(self):
        self.log = logging.getLogger("lab_monitor.server.EmailNotification")
        self.log.setLevel(logging.INFO)
        self.log.info("Initialazing EmailNotificator")

        self.receiver = 'receiver@gmail.com'
        self.sender  =  'sender@gmail.com'
        self.google_password = ''

        self.jid = xmpp.protocol.JID(self.sender)
        self.cl = xmpp.Client(self.jid.getDomain(),debug=[])
        self.cl.connect()
        self.cl.auth(self.jid.getNode(), self.google_password)

#BEWARE ABOSULTELY DISGUSTING CODE BEGINS HERE ALSO ITS NOT FINISHED YET

    def send_communication(self,signal, server, datetime):
        if signal[2] == "restored":
            comm_restored = "Communication with server {0} restored.".format(server)
            return comm_restored
        elif signal[2] == "lost":
            comm_lost = "Communication with server {0} lost. Last reading from {1}.".format(server, datetime)
            return comm_lost

    def send_server_power(self,signal, server):
        if signal[2] == "restored":
            power_server_restored = "Power restored in server {0}.".format(server)
            return power_server_restored
        elif signal[2] == "partial_loss":
            power_server_partial_loss = "Partial power loss in server {0}. Suspected PDU failure.".format(server)
            return power_server_partial_loss
    
    def send_rack_power(self,signal, rack):
        if signal[2] == "partial_loss":
            if signal[3] == "UPS":   
                power_rack_partial_loss_UPS = "Partial power loss in rack {0}. Suspected UPS failure.".format(rack)
                return power_rack_partial_loss_UPS
            elif signal[3] == "grid":
                power_rack_partial_loss_grid = "Partial power loss in rack {0}. Suspected power grid failure.".format(rack)
                return power_rack_partial_loss_grid
        elif signal[2] == "restored":
            power_rack_restored = "Power restored in rack {0}.".format(rack)
            return power_rack_restored

    def send_lab_power(self,signal, timeout):
        if signal[2] == "partial_loss":
            power_lab_partial_loss = "Partial power loss in laboratory. Suspected grid failure. Shutdown in {0} minutes.".format(timeout)
            return power_lab_partial_loss
        elif signal[2] == "restored":
            power_lab_restored = "Power restored in laboratory. Shutdown aborted."
            return power_lab_restored

    def send_server_temperature(self,signal, server, number):
        if signal[2] == "status":
            if signal[3] == "raised":
                temp_server_status_raise = "Inlet temperature in server {0} reached {1}C.".format(server, number)
                return temp_server_status_raise
            elif signal[3] == "dropped":
                temp_server_status_drop = "Inlet temperature in server {0} dropped below {1}C.".format(server, number)
                return temp_server_status_drop
        elif signal[2] == "shutdown":
            temp_server_shutdown = "Inlet temperature in server {0} reached {1}C. Shutting down the server.".format(server, number)
            return temp_server_shutdown
    
    def send_rack_temperature(self,signal, rack, number):
        if signal[2] == "status":
            if signal[3] == "raised":
                temp_rack_status_raise = "Inlet temperature in rack {0} reached {1}C.".format(rack, number)
                return temp_rack_status_raise
            elif signal[3] == "dropped":
                temp_rack_status_drop = "Inlet temperature in rack {0} dropped below {1}C.".format(rack, number)
                return temp_rack_status_drop
        elif signal[2] == "shutdown":
            temp_rack_shutdown = "Inlet temperature in rack {0} reached {1}C. Shutting down the rack.".format(rack, number)
            return temp_rack_shutdown
    
    def send_lab_temperature(self,signal, number):
        if signal[2] == "status":
            if signal[3] == "raised":
                temp_lab_status_raise = "Inlet temperature in laboratory reached {0}C.".format(number)
                return temp_lab_status_raise
            elif signal[3] == "dropped":
                temp_lab_status_drop = "Inlet temperature in laboratory dropped below {0}C.".format(number)
                return temp_lab_status_drop
        elif signal[2] == "shutdown":
            temp_lab_shutdown = "Inlet temperature in laboratory reached {0}C. Shutting down the laboratory.".format(number)
            return temp_lab_shutdown

    def send_shutdown(self, signal, server):
        if signal[2] == "init":
            shutdown_server = "Shutting down server {0}.".format(server)
            return shutdown_server
        elif signal[2] == "completed":
            shutdown_server_status = "Server {0} shutdown completed.".format(server)
            return shutdown_server_status

    def get_notification(self, signal, pos1, pos2):
        if signal[0] == "communication":
            return self.send_communication(signal, pos1, pos2)
        elif signal[0] == "power":
            if signal[1] == "server":
                return self.send_server_power(signal, pos1)
            elif signal[1] == "rack":
                return self.send_rack_power(signal, pos1)
            elif signal[1] == "lab":
                return self.send_lab_power(signal, pos1)
        elif signal[0] == "temperature":
            if signal[1] == "server":
                return self.send_server_temperature(signal, pos1, pos2)
            elif signal[1] == "rack":
                return self.send_rack_temperature(signal, pos1, pos2)
            elif signal[1] == "lab":
                return self.send_lab_temperature(signal, pos1)
        elif signal[0] == "shutdown":
            return self.send_shutdown(signal, pos1)
        else:
            return "wrong signal construction"

    def send_notification(self, signal, pos1='', pos2=''):
        """Basing on signal we recieve, we must decide what kind of notfication we want to send"""
        self.cl.sendInitPresence() 
        self.cl.send(xmpp.protocol.Message(self.receiver, self.get_notification(signal, pos1, pos2), typ='chat'))
