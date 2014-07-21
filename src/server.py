import paramiko
import time

class ESXiHypervisor:
    #initialazing - connecting to the ESXi server
    def __init__(self, hostname , username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname, username=username, password=password)

    def get_status(self, vmid):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.getstate {0} | tail -1 | awk '{{print $2}}'".format(vmid))
        output = stdout.read().strip('\n')
        return (output == "on")

    def timing(self, timeout, vmid, forced):
        print "lets start a timer"
        start = time.clock()
        elapsed = time.clock()
        while (elapsed - start)*300 < timeout:
            status = self.get_status(vmid)
            if status == False:
                return "OK"
            elapsed = time.clock()
            print "Actual running time:", (elapsed - start)*300
        if forced:
            out = self.force_shutdown_VirtualMachine(vmid)
            return out
        else:
            print "Error occurred. Status didn't change after elapsed time."
            return "ERROR"

    #IDs of VMs are stored in an array, then we loop over IDs and get their statuses
    #If status is 'on', then we shutdown the VM and we add the ID to the list of IDs that are already shutted down by us
    def status(self):
        VMSL = {}
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk '{print $1}'")
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
        while AVMSL:
            print "Active VMs: ", AVMSL
            for i in AVMSL:
                if self.get_status(int(i)):
                    err = self.shutdown_VirtualMachine(int(i))
                    print "Shutting down VM: ", i
                    if self.timing(timeout, int(i), False) == "ERROR" or err.read():
                        print "Error occurred. Status didn't change after elapsed time."
                        return "ERROR"
                else:
                    print "VMID down: ", i
                    AVMSL.remove(i)
        print "All done. Powering off"
        # self.ssh.exec_command("/sbin/shutdown.sh")
        # self.ssh.exec_command("/sbin/poweroff")

    def force_shutdown(self, timeout):
        VMSL = self.status()
        VMidSL = VMSL.keys()
        AVMSL = []
        for vmid in VMidSL:
            if VMSL[vmid]:
                AVMSL.append(vmid)
        while AVMSL:
            print "Active VMs: ", AVMSL
            for i in AVMSL:
                if self.get_status(int(i)):
                    err = self.shutdown_VirtualMachine(int(i))
                    print "Shutting down VM: ", i
                    if self.timing(timeout, int(i), True) == "ERROR" or err.read():
                        print "Error occurred. Forcing a shutdown of id=", i
                        out = self.force_shutdown_VirtualMachine(int(i))   
                else:
                    print "VMID down: ", i
                    AVMSL.remove(i)
        print "All done. Powering off"
        #self.ssh.exec_command("/sbin/shutdown.sh")
        #self.ssh.exec_command("/sbin/poweroff")

    def force_shutdown_VirtualMachine(self, VM_id, timeout = 0):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.off {0}".format(VM_id))
        if timeout > 0:
            return self.timing(timeout, VM_id, True)
        return stdout

    def shutdown_VirtualMachine(self, VM_id, timeout = 0, forced = False):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.shutdown {0}".format(VM_id))
        if timeout > 0:
            out =  self.timing(timeout, VM_id, forced)
            print out
            return out
        if stderr.read() != "":
            return "ERROR"

class ESXiVirtualMachine:

    def __init__(self, vmid, hypervisor):
        self.id = vmid
        self.ESXiHypervisor = hypervisor

    #Returning status of a VM
    def status(self):
        return self.ESXiHypervisor.get_status(self.id)

    #Shutting down a VM
    def shutdown(self):
        return self.ESXiHypervisor.shutdown_VirtualMachine(self.id)

    #Force shutting down of a VM
    def force_shutdown(self):
        return self.ESXiHypervisor.force_shutdown_VirtualMachine(self.id)


