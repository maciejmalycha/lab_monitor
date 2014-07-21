import server
import sys
import argparse

def status(args):
    print "Getting status of ESXi server", args.address

def shutdown(args):
    if args.force:
        print "Forced shutdown of ESXi server", args.address, "timeout =", args.timeout
    else:
        print "Shutdown of ESXi server", args.address, "timeout=", args.timeout

parser = argparse.ArgumentParser(prog="esxi", description='Manage ESXi server')
subparsers = parser.add_subparsers()
parser_status = subparsers.add_parser("status", help="Display status of ESXi server")
parser_status.add_argument("address", help="Address of ESXi server")
parser_status.set_defaults(func=status)
parser_shutdown = subparsers.add_parser("shutdown", help="Shutdown ESXi server")
parser_shutdown.add_argument("-f", "--force", action="store_true", help="Force shutdown (possible data loss)")
parser_shutdown.add_argument("-t", "--timeout", action="store", type=int, default=300, help="Server shutdown timeout in seconds")
parser_shutdown.add_argument("address", help="Address of ESXi server")
parser_shutdown.set_defaults(func=shutdown)

args = parser.parse_args()
args.func(args)

#==============================================================================
# args = sys.argv[1].split()
# print args
# target = args[0]
# function = args[1]
# if args[2] == "-t" and args[4] == "-f":
#	host = args[5]
# elif args[2] == "-t" and args[4] != "-f":
#	host = args[4]
# else:
#	host = args[2]
# if target == "esxi_vm":
#	vmid = int(args[-1])
#
# Example = server.ESXiHypervisor(host, "root", "ChangeMe")
#
# if target == "esxi":
#	if function == "status":
#		print "Getting statuses of VMs"
#		print Example.status()
#	elif function == "shutdown":
#		print "Shutting down VMs"
#		if Example.shutdown() == "ERROR":
#			Example.force_shutdown()
# elif target == "esxi_vm":
#	if function == "status":
#		print "Getting status of VM: ", vmid
#		print Example.get_status(vmid)
#	elif function == "shutdown" and args[4] == "-f":
#		print "Forcing a shutdown of VM: ", vmid
#		out = Example.force_shutdown_VirtualMachine(vmid)
#		print out.read()
#	elif function == "shutdown":
#		print "Shutting down VM: ", vmid
#		err = Example.shutdown_VirtualMachine(vmid)
#		if err.read() != "":
#			print "Error occured. Forcing a shutdown of VM: ", vmid
#			out = Example.force_shutdown_VirtualMachine(vmid)
#==============================================================================
