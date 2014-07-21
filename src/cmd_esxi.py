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