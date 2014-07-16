import paramiko

class ESXiHypervisor:
    #initialazing - connecting to the ESXi server
    def __init__(self, hostname, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname, username=username, password=password)
        self.AVMIDS = []
        self.VMSL = {}

    #IDs of VMs are stored in an array, then we loop over IDs and get their statuses
    #If status is 'on', then we shutdown the VM and we add the ID to the list of IDs that are shutted down by us
    def status(self):
        self.VMIDin, self.VMIDout, self.VMIDerr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk '{print $1}'")
        for i in self.VMIDout:
            VM_id = int(i)
            Act_VM = ESXiVirtualMachine(VM_id)
            Act_VM.stat = Act_VM.status()
            if Act_VM.stat:
                self.AVMIDS.append(Act_VM)
            self.VMSL[Act_VM.id] = Act_VM.stat
        return self.VMSL

    #Shutting down every working VM
    def shutdown(self):
        while self.AVMIDS.size:           #probably unnecessary loop
            print "AVMIDS:", self.AVMIDS
            for i in self.AVMIDS:
                if i.stat == False:
                    print "VMID down:", i
                    self.AVMIDS.remove(i) #if element is unique, then this should work, otherwise we should just pop from the front of the list
        print "All done. Powering off"
        self.shutdown()         #shutting down the hypervisor after work is done

    #Shutting down the hypervisor
    def force_shutdown(self):
        self.ssh.exec_command("/sbin/shutdown.sh")
        self.ssh.exec_command("/sbin/poweroff")

class ESXiVirtualMachine:

    def __init__(self, VMid):
        self.id = VMid
        self.stat = None

    #Returning status of VM
    def status(self):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.getstate " + self.id + "| tail -1 | awk '{print $2}'")
        if str(stdout) == 'on':
            self.stat = True
            return self.stat
        else:
            self.stat = False
            return self.stat

    #Shutting down VM
    def shutdown(self):
        try:
            self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.shutdown " + self.id)
            self.stat = False
        except paramiko.SSHException:
            self.force_shutdown()

    def force_shutdown(self):
        pass


