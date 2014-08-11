#!/usr/bin/env python

import sys
import os
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning) # xmpppy raises them

def error(text):
    print "\033[91m"+text+"\033[0m"
    sys.exit(1)

def success(text):
    print "\033[92m"+text+"\033[0m"

print "Welcome to lab_monitor v. 1.0.0"


if sys.version_info < (2,6):
    error("You must use Python 2.6 or newer")
success("Python version is OK")

try:
    import flask
    import yaml
    import sqlalchemy
    import argparse
    import paramiko
    import redis
    import xmpp
except ImportError as e:
    venv = "" if hasattr(sys, 'real_prefix') else "\nHint: you are not running inside a virtualenv"
    error("{0}. Did you run `pip install -r requirements.txt`?{1}".format(e, venv))
except Exception as e:
    error("Error: {0}".format(e))
success("All necessary modules are available")

try:
    f = open('config.yaml')
    confyml = f.read()
    f.close()
except Exception as e:
    error("Cannot read config file. {0}".format(e))

try:
    config = yaml.load(confyml)
except Exception as e:
    error("Cannot parse config file. {0}".format(e))
success("Config file successfully opened and parsed")

try:
    keys = {
        'num_racks': int,
        'database': str,
        'logging_dir': str,
        'temperature': list,
        'alarm_delay': int,
        'shutdown_timeout': int,
        'xmpp': dict,
        'redis': dict
    }

    for key, type_ in keys.iteritems():
        if type(config[key]) is not type_:
            error("Configuration key '{0}' must be of type {1}".format(key, type_.__name__))
except KeyError as e:
    error("Configuration key {0} not found".format(e))
except Exception as e:
    error("Error in config file detected: {0}".format(e))
success("All expected keys exist in the config file")

for s in config['temperature']:
    sensor = s.get('sensor') or error("Temperature config key 'sensor' not found")
    warning = s.get('warning') or error("Temperature config key 'warning' not found")
    critical = s.get('critical') or error("Temperature config key 'critical' not found")

    if type(warning) is not int or type(critical) is not int:
        error("Temperature thresholds (warning and critical) must be int")

    if critical < warning:
        error("Temperature critical level cannot be less than warning level")
success("Temperature alarms are configured properly")


try:
    path = config['logging_dir']
    if not os.path.isdir(path):
        error("Specified logging path is not a valid directory")
    if path.endswith('/'):
        error("Logging path has an unnecessary trailing slash")
    if os.path.realpath(path) != path:
        error("Logging path is not absolute (should be {0})".format(os.path.realpath(path)))
    if not os.access(path, os.W_OK):
        error("Logging directory is not writable")
except Exception as e:
    error("Logging path is invalid")
success("Logging path is valid")

try:
    engine = sqlalchemy.create_engine(config['database'])
    engine.connect()
except Exception as e:
    error("Cannot connect to specified database. {0}".format(e))
success("Database is available")

try:
    red = redis.StrictRedis(**config['redis'])
except Exception as e:
    error("Cannot connect to Redis server. {0}".format(e))
success("Redis server is available")

try:
    jid = xmpp.protocol.JID(config['xmpp']['sender'])
    cl = xmpp.Client(jid.getDomain(),debug=[])
    cl.connect() or error("Cannot connect to XMPP server")
    cl.auth(jid.getNode(), config['xmpp']['password']) or error("Wrong XMPP credentials!".format(jid))
except Exception as e:
    error("XMPP doesn't work properly. {0}".format(e))
success("XMPP works")

print
success("Congratulations! All tests passed.")
print "To start the web frontend, run `src/main.py`"
print "To start the monitor, run `src/monitor.py`"
