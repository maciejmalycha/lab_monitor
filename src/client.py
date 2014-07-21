import server
import sys
from optparse import OptionParser

"""
parser = OptionParser()
parser.add_option("-t", "--timeout", dest = "value", help = "set timeout value in seconds", metavar = "SECS")
parser.add_option("-f", "--force", dest = "force", default = False, help = "use force option to force_shutdown")
(options, args) = parser.parse_args()
"""

args = sys.argv[1].split()
print args
target = args[0]
function = args[1]
if args[2] == "-t" and args[4] == "-f":
	host = args[5]
elif args[2] == "-t" and args[4] != "-f":
	host = args[4]
else:
	host = args[2]
if target == "esxi_vm":
	vmid = int(args[-1])

Example = server.ESXiHypervisor(host, "root", "ChangeMe")

if target == "esxi":
	if function == "status":
		print "Getting statuses of VMs"
		print Example.status()
	elif function == "shutdown":
		print "Shutting down VMs"
		if Example.shutdown() == "ERROR":
			Example.force_shutdown()
elif target == "esxi_vm":
	if function == "status":
		print "Getting status of VM: ", vmid
		print Example.get_status(vmid)
	elif function == "shutdown" and args[4] == "-f":
		print "Forcing a shutdown of VM: ", vmid
		out = Example.force_shutdown_VirtualMachine(vmid)
		print out.read()
	elif function == "shutdown":
		print "Shutting down VM: ", vmid
		err = Example.shutdown_VirtualMachine(vmid)
		if err.read() != "":
			print "Error occured. Forcing a shutdown of VM: ", vmid
			out = Example.force_shutdown_VirtualMachine(vmid)
			print out.read()			