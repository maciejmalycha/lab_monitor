import server
import sys
import argparse

def status(args):
	pass

def shutdown(args):
	rack = server.Rack(args.id)
	if args.force:
		rack.log.info("Forced shutdown of rack ", args.id, "timeout =", args.timeout)
		rack.force_shutdown(args.timeout)
	else:
		rack.log.info("Shutdown of rack", args.id, "timeout=", args.timeout)
		rack.shutdown(args.timeout)

parser = argparse.ArgumentParser(prog="rack", description='Manage racks')
subparsers = parser.add_subparsers()
parser_status = subparsers.add_parser("status", help="Display status of ESXi servers in the rack")
parser_status.add_argument("id", help="ID of rack")
parser_status.set_defaults(func=status)
parser_shutdown = subparsers.add_parser("shutdown", help="Shutdown whole rack")
parser_shutdown.add_argument("-f", "--force", action="store_true", help="Force shutdown (possible data loss)")
parser_shutdown.add_argument("-t", "--timeout", action="store", type=int, default=300, help="Server shutdown timeout in seconds")
parser_shutdown.add_argument("id", help="ID of rack")
parser_shutdown.set_defaults(func=shutdown)

args = parser.parse_args()
args.func(args)