import logging
import time

import gevent

class MinuteWorker(object):
    """A base class for workers that do some specific task in regular intervals of time"""

    use_gevent = True # should the tasks be performed concurrently as gevent.Greenlets?
    logger_name = 'lab_monitor.minuteworker.MinuteWorker'

    def __init__(self):
        self.state = "starting..."
        self.state_stream = None
        self.sleep = None
        self.log = logging.getLogger(self.logger_name)
        self.loop = False

    def start(self):
        """Override this function so that it prepares everything and starts the main loop afterwards"""
        return self.main_loop()

    def tasks(self):
        """Override this function. It should return a list of tasks to execute,
        each in format (callable, (arg1, arg2, ...)). If there are no arguments,
        use an empty tuple as the 2nd element."""
        return []

    def update_state(self, state):
        """Sets new worker state (starting, working, idle, stopping, off) and pushes it to a stream, if available"""
        self.state = state
        if self.state_stream is not None:
            self.state_stream.write(self.state)

    def main_loop(self):
        """Calls the tasks every minute"""
        self.loop = True
        try:
            while self.loop:
                try:
                    t0 = time.time()

                    self.update_state("working")

                    tasks = self.tasks()
                    if self.use_gevent:
                        jobs = [gevent.spawn(task, *args) for task, args in tasks]
                        gevent.joinall(jobs)
                    else:
                        for task, args in tasks:
                            task(*args)

                    t = time.time()
                    dt = t-t0
                    wait = 60-dt

                    # wait until next minute, unless it's time to finish
                    if self.loop and wait>0:
                        self.update_state("idle")
                        self.log.info("Waiting %u seconds...", wait)
                        # it should sleep, but also be able to wake up when stop is called
                        self.sleep = gevent.spawn(gevent.sleep, wait)
                        self.sleep.join()

                except Exception as e:
                    self.log.exception("Exception happened: %s", e)

            self.update_state("off")
            self.log.info("Exiting")
            return True
                
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stops the main loop. If it's active, waits until the end of current iteration. If it's idle, breaks out of sleep immediately"""
        if self.loop:
            self.log.info("Stop called")
            self.loop = False
            self.update_state("stopping")
            if self.sleep is not None:
                self.sleep.kill()
        else:
            self.log.info("Already outside main loop")