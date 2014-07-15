import paramiko

class ESXiHypervisor:
    #initialazing - connecting to the ESXi server
    def __init__(self, hostname, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname, username=username, password=password)
        self.AVMIDS = []
        return self.ssh, self.ssh.open_sftp()

    #IDs of VMs are stored in an array, then we loop over IDs and get their statuses
    #If status is 'on', then we shutdown the VM and we add the ID to the list of IDs that are shutted down by us
    def status(self):
        self.VMID = self.exec_command("/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk '{print $1}'")
        for i in self.VMID:
            if str(i[1].status) == 'on':
                self.AVMIDS.append(i)
                i.shutdown()        #probably bad call, it should be called on ESXIVM object
        self.force_shutdown()

    #Shutting down the hypervisor
    def shutdown(self):
        self.exec_command("/sbin/shutdown.sh")
        self.exec_command("/sbin/poweroff")

    #Shutting down every working VM
    def force_shutdown(self):
        while self.AVMIDS.size:
            print "AVMIDS:", self.AVMIDS
            for i in self.AVMIDS:
                if str(i.status()) == 'off':
                    print "VMID down:", i
                    self.AVMIDS.remove(i)
        print "All done. Powering off"
        self.shutdown()

class ESXiVirtualMachine:

    #Returning status of VM
    def status(self):
        stat = self.exec_command("/usr/bin/vim-cmd vmsvc/power.getstate " + self + "| tail -1 | awk '{print $2}'")
        return stat[1]

    #Shutting down VM
    def shutdown(self):
        output = self.exec_command("/usr/bin/vim-cmd vmsvc/power.shutdown " + self)
        if str(output[2]):
            self.force_shutdown()

    def force_shutdown(self):
        pass


