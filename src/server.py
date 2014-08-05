import logging
import time

import paramiko

import database

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