import logging
import time
import threading

class MinuteWorker(object):
    """A base class for workers that do some specific task in regular intervals of time"""

    threaded = True # whether to perform each task as a separate thread
    logger_name = 'lab_monitor.minuteworker.MinuteWorker'
    interval = 60

    def __init__(self):
        self.state = "starting..."
        self.state_updater = None
        self.sleep = None
        self.log = logging.getLogger(self.logger_name)
        self.loop = False

    def start(self):
        """Override this function so that it prepares everything and starts the main loop afterwards"""
        self.update_state("starting...")
        return self.main_loop()

    def tasks(self):
        """Override this function. It should return a list of tasks to execute,
        each in format (callable, (arg1, arg2, ...)). If there are no arguments,
        use an empty tuple as the 2nd element."""
        return []

    def update_state(self, state):
        """Sets new worker state (starting, working, idle, stopping, off) and pushes it to a stream, if available"""
        self.state = state
        if callable(self.state_updater):
            self.state_updater(self.state)

    def main_loop(self):
        """Calls the tasks every minute"""
        self.loop = True
        self.sleeper = threading.Event()
        try:
            while self.loop:
                try:
                    t0 = time.time()

                    self.update_state("working")
 
                    tasks = self.tasks()
                    if self.threaded:
                        workers = []
                        for task, args in tasks:
                            worker = threading.Thread(target=task, args=args)
                            workers.append(worker)
                            worker.start()
                        for worker in workers:
                            worker.join()
                    else:
                        for task, args in tasks:
                            task(*args)

                    t = time.time()
                    dt = t-t0
                    wait = self.interval-dt

                    # wait until next minute, unless it's time to finish
                    if self.loop and wait>0:
                        self.update_state("idle")
                        self.log.info("Waiting %u seconds...", wait)
                        # it should sleep, but also be able to wake up when stop is called
                        self.sleeper.wait(wait)

                except Exception as e:
                    self.log.exception("Exception happened: %s", e)
                
        except KeyboardInterrupt:
            self.stop()

    def wait(self, secs):
        """Delays execution for given number of seconds, but breaks
        out of it if self.loop is set to False"""
        time.sleep(secs%1) # fractional part
        secs = int(secs)
        while self.loop and secs > 0:
            time.sleep(1)
            secs -= 1

    def stop(self):
        """Stops the main loop. If it's active, waits until the end of current iteration. If it's idle, breaks out of sleep immediately"""
        if self.loop:
            self.log.info("Stop called")
            self.loop = False
            self.sleeper.set()
            self.update_state("stopping")
        else:
            self.log.info("Already outside main loop")

        self.update_state("off")