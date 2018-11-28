"""Defines the actual operating classes for Tapestry.py. There is essentially
no executable code in this script - it's just used to hold the working classes
for tapestry.py.

Classes are to be organized by general purpose - see block comments for guidance.

"""

import bz2
import multiprocessing as mp
import os
import shutil
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
                    self.ret.put('%s: Exiting' % proc_name)
                self.queue.task_done()
                break
            try:
                debug_message = next_task()
                self.ret.put(debug_message)
            except TypeError:
                self.ret.put("Something has gone wrong - unexpected item in queue.")
            self.queue.task_done()
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
        return ("Added %s to tarfile %s" % (self.tarf, self.b))


class TaskTarUnpack(object):
    """A simple object that describes a file to pull from a particular tarfile
    and puts it back where it belongs. Absolute paths required.
    """
    def __init__(self, tar, fid, category_dir, path_end):
        """Initializing this object gives it all the information it needs to
        unpack one particular file back to its original position in the
        filesystem or to the fallback location.

        :param tar: string describing the absolute path of the relevant tarball
        :param fid: The GUID FID that the file has been packed into the tarball as.
        :param category_dir: full path to the top of the category.
        :param path_end: sub-path from the category including the filename
        """
        self.tar = tar
        self.fid = fid
        self.catdir = category_dir
        self.pathend = path_end

    def __call__(self):
        path_end = self.pathend.strip('~/')
        abs_path_out = os.path.join(self.catdir, path_end)
        placement, name_proper = os.path.split(
            abs_path_out)
        # split the pathend component into the subpath from the category dir, and the original filename.
        with tarfile.open(self.tar, "r") as tf:
            tf.extract(self.fid, path=placement)  # the file is now located where it needs to be.
            placed = os.path.join(placement, self.fid)
            os.rename(placed, abs_path_out)  # and now it's named correctly.
        return ("Restored %s to %s" % (self.fid, abs_path_out))


class TaskCompress(object):
    """A simple task that points exactly to a tarfile to compress, and then
    compresses it to a specified level
    """

    def __init__(self, t, lvl):
        """Defines the absolute path to a tarfile and the level (1-9) of
        compression to apply.

        :param t: Absolute path to a tarfile
        :param lvl: Integer between 1 and 9 which determines the compression level
        """
        self.tarf = t
        self.level = lvl

    def __call__(self):
        with open(self.tarf, "rb") as b:
            bz2d = self.tarf+".bz2"
            bz2f = bz2.BZ2File(bz2d, "wb", compresslevel=self.level)
            shutil.copyfileobj(b, bz2f)
        return "Compressed %s to level %s" % (self.tarf, self.level)
