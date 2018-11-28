"""Defines the actual operating classes for Tapestry.py. There is essentially
no executable code in this script - it's just used to hold the working classes
for tapestry.py.

Classes are to be organized by general purpose - see block comments for guidance.

"""

import multiprocessing as mp
import os
import tarfile

# Define Process Classes


class ChildProcess(mp.Process):
    """A simple, logicless worker process which iterates against a queue. This
    expects to find either a callable "task" class in the queue or the value
    None, which indicates the process should exit.
    """

    def __init__(self, queue_tasking, queue_complete, working_directory, debug=False):
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
        self.ret = queue_complete
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
            try:
                next_task()
            except TypeError:
                print("Something has gone wrong - unexpected item in queue.")
            self.queue.task_done()
            self.ret.put("0")  # Any value will suffice.
        return


class TaskTarBuild(object):
    """A simple task object which instructs the process to add a particular
    file to a particular tarfile, all fully enumerated.
    """

    def __init__(self, tarf, FID, PATH, index, locks):
        """
        Create the tarfile or, otherwise, add a file to it.
        :param tarf: which tarfile to use, relative to the working directory
        :param FID: GUID FID as a string.
        :param PATH: absolute path to the file in need of backup
        :param index: appropriate index number for the lock to acquire.
        :param locks: Locks dictionary which should be used.
        """
        self.tarf = tarf
        self.a = FID
        self.b = PATH
        self.index = index  # index number of the appropriate mutex
        self.locks = locks

    def __call__(self):
        if os.path.exists(self.tarf):  # we need to know if we're starting a new file or not.
            fLock = self.locks[self.index]  # Aquires the lock indicated in the index value from the master
            fLock.acquire()
            tar = tarfile.open(name=self.tarf, mode="a:")
            tar.add(self.b, arcname=self.a, recursive=False)
            tar.close()
            fLock.release()