"""Defines the actual operating classes for Tapestry.py. There is essentially
no executable code in this script - it's just used to hold the working classes
for tapestry.py.

Classes are to be organized by general purpose - see block comments for guidance.

"""

import multiprocessing as mp
import os

# Define Process Classes

class ChildProcess(mp.Process):
    """A simple, logicless worker process which iterates against a queue. This
    expects to find either a callable "task" class in the queue or the value
    None, which indicates the process should exit.
    """

    def __init__(self, queue_tasking, working_directory, debug=False):
        """Initialize the class. Must provide the queue to attach to, the
        working directory to use, and a debug flag.

        :param queue_tasking: mp.Queue object used for multiprocess communication.
        :param working_directory: String to the absolute path of the desired
        working directory.
        :param debug: Boolean, activates the debugging statement.
        """
        mp.Process.__init__(self)
        self.queue = queue_tasking
        self.debug = debug
        os.chdir(working_directory)

    def run(self):
        proc_name = self.name
        while True:
            next_task = self.queue.get()
            if next_task is None:
                if self.debug:
                    print('%s: Exiting' % proc_name)
                self.queue.task_done()
                break
            next_task()
            self.queue.task_done()
        return

