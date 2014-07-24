import server
import sys
import argparse

def status(args):
	lab = server.Laboratory()
	lab.status()

def shutdown(args):
	lab = server.Laboratory()
	if args.force:
		lab.log.info("Forced shutdown of lab ", "timeout =", args.timeout)
		lab.force_shutdown(args.timeout)
	else:
		lab.log.info("Shutdown of lab", "timeout=", args.timeout)
		lab.shutdown(args.timeout)

parser = argparse.ArgumentParser(prog="lab", description='Manage laboratory')
subparsers = parser.add_subparsers()
parser_status = subparsers.add_parser("status", help="Display status of laboratory")
parser_status.set_defaults(func=status)
parser_shutdown = subparsers.add_parser("shutdown", help="Shutdown whole laboratory")
parser_shutdown.add_argument("-f", "--force", action="store_true", help="Force shutdown (possible data loss)")
parser_shutdown.add_argument("-t", "--timeout", action="store", type=int, default=300, help="Server shutdown timeout in seconds")
parser_shutdown.set_defaults(func=shutdown)

args = parser.parse_args()
args.func(args)