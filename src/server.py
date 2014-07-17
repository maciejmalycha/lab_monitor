#TODO: To poprawna skladnia, ale sa dobre powody zeby tak nie robic. See PEP8
#      http://legacy.python.org/dev/peps/pep-0008/
import paramiko, time

class ESXiHypervisor:
    #initialazing - connecting to the ESXi server
    #TODO: own_id nie jest uzywany - mozna usunac
    def __init__(self, hostname , username, password , own_id):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname, username=username, password=password)
        #TODO: Nie ma potrzeby, zeby te informacje byly przechowywane w klasie
        #      mozna usunac te linie
        self.AVMIDS = []
        self.VMSL = {}
        self.H_id = own_id

    #TODO: Req_id - niepoprawna kapitalizacja - PEP8. Lepiej pasuje vmid
    def get_status(self, Req_id):
        #TODO: Zamiast + lepiej uzyc "... {} ...".format(vmid) see https://docs.python.org/2/library/string.html#string-formatting
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.getstate " + str(Req_id) + "| tail -1 | awk '{print $2}'")
        #TODO: stdout jest strumieniem - lepiej nie zmieniac typu zmiennej w metodzie
        #      (latwo sie pomylic). No i mozna zastosowac chaining. Te dwie linie
        #      mozna zastapic przez: output = stdout.read().strip('\n')
        stdout = stdout.read()
        stdout = stdout.strip('\n')

        #TODO: Zamiast tych czterech linii wystarczy: return (stdout == "on")
        if stdout == "on":
            return True
        else:
            return False
        
    #IDs of VMs are stored in an array, then we loop over IDs and get their statuses
    #If status is 'on', then we shutdown the VM and we add the ID to the list of IDs that are already shutted down by us
    def status(self):
        #TODO: Nie ma potrzeby zeby zadna z tych zmiennych byla przechowywana w klasie
        #      wystarczy ze beda lokalne. Plus uwagi co do kapitalizacji, chainingu, zmiany typu jak wyzej.
        self.VMIDin, self.VMIDout, self.VMIDerr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk '{print $1}'")
        self.VMIDout = self.VMIDout.read()
        self.VMIDout = self.VMIDout.split()
        
        for i in self.VMIDout:
            VM_id = int(i)
            #TODO: Przejscie przez ESXiVirtualMachine jest w zasadzie niepotrzebne
            #      Wystarczy uzyc self.get_status(vmid)
            Act_VM = ESXiVirtualMachine(VM_id, self.H_id, self)
            #TODO: Nie ma potrzeby zapisywac sobie tego w kalsie - mozna uzyc zmiennej
            #      lokalnej
            Act_VM.stat = Act_VM.status()
            #TODO: Metoda probuje robic dwie rzeczy na raz - zwrocic status i przygotowac liste aktywnych
            #      vm dla self.shutdown(). Ta druga funkcja jest niepotrzebna.
            if Act_VM.stat:
                self.AVMIDS.append(Act_VM)
            self.VMSL[Act_VM.id] = Act_VM.stat
        return self.VMSL

    #Shutting down every working VM
    #TODO: Algorytm w skrypcie byl inny:
    #      1. Wez liste wszystkich aktywnych VM
    #      2. Wydaj kazdemu z nich polecenie power.shutdown
    #      3. Sprawdzaj ich status dopoki wszystkie sie nie wylacza
    # Dodatkowo mozna wprowadzic wykrywanie czy sa zainstalowane VMWare tools
    # i dodac timeout po ktorym komenda zwroci blad o ile wszystkie maszyny sie
    # nie zamkna.
    def shutdown(self):
        for i in self.AVMIDS:
            if i.stat == False:
                print "VMID down:", i.id
            else:
                result = i.shutdown()
                if result.read() == "":
                    print i.id, "is down"
                    i.stat = False
                else:
                    print i.id, "IS NOT down"
                    print "Shutting down", i.id, " with power.off command"
                    i.force_shutdown()
                    i.stat = False
        time.sleep(10)

        print "All done. Powering off"
        #self.force_shutdown()         #shutting down the hypervisor after work is done

    #Shutting down the hypervisor
    #TODO: Force shutdown powinno dzialac podobnie jak shutdown. Z tym, ze powinno
    #      zamknac maszyne nawet w przypadku gdy nie ma tooli lub wystapil timeout
    #      Jesli toole sa i timeout nie wystapil, dzialanie nie powinno sie roznic
    #      od shutdown()
    def force_shutdown(self):
        self.ssh.exec_command("/sbin/shutdown.sh")
        self.ssh.exec_command("/sbin/poweroff")

    def force_shutdown_VirtualMachine(self, VM_id):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.off " + str(VM_id))
        time.sleep(1)

    def shutdown_VirtualMachine(self, VM_id):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/vim-cmd vmsvc/power.shutdown " + str(VM_id))
        time.sleep(1)
        return stderr

class ESXiVirtualMachine:

    #TODO: H_id nie jest uzywany i moze byc usuniety
    def __init__(self, VMid, H_id, hypervisor):
        self.id = VMid
        self.stat = None
        self.H_id = H_id
        self.ESXiHypervisor = hypervisor

    #Returning status of a VM
    def status(self):
        #TODO: Prawdopodobnie chodzi o self.ESXiHypervisor.get_status(self.id)
        return ESXiHypervisor.get_status(self.ESXiHypervisor, self.id)

    #Shutting down a VM
    def shutdown(self):
        return ESXiHypervisor.shutdown_VirtualMachine(self.ESXiHypervisor, self.id)
    
    #Force shutting down of a VM    
    def force_shutdown(self):
        return ESXiHypervisor.force_shutdown_VirtualMachine(self.ESXiHypervisor, self.id)


