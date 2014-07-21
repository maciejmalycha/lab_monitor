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
    #TODO: Algorytm w skrypcie byl inny:
    #      1. Wez liste wszystkich aktywnych VM
    #      2. Wydaj kazdemu z nich polecenie power.shutdown
    #      3. Sprawdzaj ich status dopoki wszystkie sie nie wylacza
    # Dodatkowo mozna wprowadzic wykrywanie czy sa zainstalowane VMWare tools
    # i dodac timeout po ktorym komenda zwroci blad o ile wszystkie maszyny sie
    # nie zamkna.
    def shutdown(self):
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
                    time.sleep(5)
                    if err.read():
                        return "ERROR"
                else:
                    print "VMID down: ", i
                    AVMSL.remove(i)
        print "All done. Powering off"
        # self.ssh.exec_command("/sbin/shutdown.sh")
        # self.ssh.exec_command("/sbin/poweroff")
    #Shutting down the hypervisor
    #TODO: Force shutdown powinno dzialac podobnie jak shutdown. Z tym, ze powinno
    #      zamknac maszyne nawet w przypadku gdy nie ma tooli lub wystapil timeout
    #      Jesli toole sa i timeout nie wystapil, dzialanie nie powinno sie roznic
    #      od shutdown()
    def force_shutdown(self):
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
                    time.sleep(5)
                    # print err.read()
                    if err.read() != "":
                        print "Forcing shutdown vm: ", int(i)
                        self.force_shutdown_VirtualMachine(int(i))
                else:
                    print "VMID down: ", i
                    AVMSL.remove(i)
        print "All done. Powering off"
        #self.ssh.exec_command("/sbin/shutdown.sh")
        #self.ssh.exec_command("/sbin/poweroff")

    def force_shutdown_VirtualMachine(self, VM_id):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.off {0}".format(VM_id))
        return stdout
    def shutdown_VirtualMachine(self, VM_id):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.shutdown {0}".format(VM_id))
        return stderr

class ESXiVirtualMachine:

    def __init__(self, vmid, hypervisor):
        self.id = vmid
        self.hypervisor = hypervisor

    #Returning status of a VM
    def status(self):
        return self.hypervisor.get_status(self.id)

    #Shutting down a VM
    def shutdown(self):
        return self.hypervisor.shutdown_VirtualMachine(self.id)

    #Force shutting down of a VM
    def force_shutdown(self):
        return self.hypervisor.force_shutdown_VirtualMachine(self.id)


