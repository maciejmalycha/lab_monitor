import os
import os.path
import signal
import time

getpid = os.getpid

def wait(pid, intvl=1):
    while process_exists(pid):
        time.sleep(intvl)

def process_exists(pid):
    return os.path.exists("/proc/{0}".format(pid))

def intrr(pid):
    os.kill(int(pid), signal.SIGINT)

def kill_wait(pid):
    kill_if(pid)
    return wait(pid)

def kill_if(pid):
    if process_exists(pid):
        intrr(pid)