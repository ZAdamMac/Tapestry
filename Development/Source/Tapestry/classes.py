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

    def __init__(self, tarf, fid, path, index, locks):
        """
        Create the tarfile or, otherwise, add a file to it.
        :param tarf: which tarfile to use, relative to the working directory
        :param fid: GUID FID as a string.
        :param path: absolute path to the file in need of backup
        :param index: appropriate index number for the lock to acquire.
        :param locks: Locks dictionary which should be used.
        """
        self.tarf = tarf
        self.a = fid
        self.b = path
        self.index = index  # index number of the appropriate mutex
        self.locks = locks

    def __call__(self):
        if os.path.exists(self.tarf):  # we need to know if we're starting a new file or not.
            f_lock = self.locks[self.index]  # Aquires the lock indicated in the index value from the master
            f_lock.acquire()
            tar = tarfile.open(name=self.tarf, mode="a:")
            tar.add(self.b, arcname=self.a, recursive=False)
            tar.close()
            f_lock.release()
        return "Added %s to tarfile %s" % (self.tarf, self.b)


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
        return "Restored %s to %s" % (self.fid, abs_path_out)


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


class TaskDecompress(object):
    """A simple task that points exactly to a tarfile to decompress. The task
    can determine for itself if the file actually needs decompressing at runtime.
    """

    def __init__(self, t):
        """Defines the absolute path to a file to check for compression.

        :param t: Absolute path to a tarfile
        """
        self.tarf = t

    def __call__(self):
        with open(self.tarf, "rb") as file:
            signature = file.read()
            if signature.startswith(b"BZh"):  # Microheader that indicates a BZ2 file.
                shutil.copy(self.tarf, (self.tarf + ".temp"))
                with bz2.BZ2File(self.tarf + ".temp", "rb") as compressed:
                    with open(self.tarf, "wb") as uncompressed:
                        shutil.copyfileobj(compressed, uncompressed)
                os.remove(self.tarf+".temp")  # No sense in cluttering up the drive.
                return "Decompressed %s" % self.tarf
            else:
                return "File is already decompressed."


class TaskEncrypt(object):
    """This task takes an argument for the fingerprint to use, the file to be
    encrypted, and the directory currently used for output.

    """
    def __init__(self, t, fp, out, gpg):
        """This object expects the following arguments in order to signify a
        tarfile which needs to be encrypted. Calling the task will cause the
        tarfile to be encrypted using the gpg object passed to it at runtime.

        :param t: an absolute path denoting the location of the tarfile.
        :param fp: the fingerprint of the PGP key to use.
        :param out: The absolute path to the output directory.
        :param gpg: An gnupg.GPG object provided to allow an interface with
        the local GPG runtime.
        """
        self.tarf = t
        self.fp = fp
        self.out = out
        self.gpg = gpg

    def __call__(self):
        with open(self.tarf, "r") as p:
            path, tapped = os.path.split(self.tarf)
            tapped = tapped.strip(".bz2")
            tapped = tapped.replace(".tar", ".tap")
            tgtOutput = os.path.join(self.out, tapped)
            with open(self.tarf, "rb") as tgt:
                k = self.gpg.encrypt_file(tgt, self.fp, output=tgtOutput, armor=True, always_trust=True)
            if k.ok:
                return "Encryption Success for %s." % self.tarf
            elif not k.ok:
                return "Encryption Failed for %s, status: %s" % (self.tarf, k.status)


class TaskDecrypt(object):
    """This task contains both the information and method to take a Tapestry
    blockfile and decrypt it. This task is naive in that it relies on another
    task to do signature verification.

    """
    def __init__(self, block, working_directory, gpg):
        """This object requires the following arguments in order to fetch,
        open, and decrypt a single block, outputting the contents to a
        working directory, based on the operation of a gnupg.GPG object.

        :param block: Absolute path to the block to be decrypted.
        :param working_directory: Absolute path to the output directory.
        :param gpg:
        """
        self.tap_file = block
        self.tap_name = os.path.split(block)[1]
        self.absolute_output= os.path.join(working_directory, self.tap_name)
        self.gpg = gpg

    def __call__(self):
            with open(self.tap_file, "rb") as tgt:
                k = self.gpg.decrypt_file(tgt, output=self.absolute_output, always_trust=True)
            if k.ok:
                return "Decryption Success for %s." % self.tap_name
            elif not k.ok:
                return "Decryption Failed for %s, status: %s" % (self.tap_name, k.status)

class TaskSign(object):
    """This task takes an argument for the fingerprint to use, the file to be
    signed, the output directory, and a GPG object.

    """
    def __init__(self, t, fp, out, gpg):
        """This object expects the following arguments in order to sign a
        tapfile which needs to be encrypted. Calling the task will cause the
        tapfile to be signed using the gpg object passed to it at runtime.

        :param t: an absolute path denoting the location of the tapfile.
        :param fp: the fingerprint of the PGP key to use.
        :param out: The absolute path to the output directory.
        :param gpg: An gnupg.GPG object provided to allow an interface with
        the local GPG runtime.
        """
        self.file = t
        self.fp = fp
        self.out = out
        self.gpg = gpg

    def __call__(self):
        with open(self.file, "r") as p:
            path, tapped = os.path.split(self.file)
            absolute_output = os.path.join(self.out, tapped)
            absolute_output += ".sig"
            k = self.gpg.sign_file(self.file, keyid=self.fp, output=absolute_output, detach=True)
            if k.status == "signature created":
                return "Signing Success for %s." % tapped
            else:
                return "Signing Failed for %s, status: %s" % (tapped, k.status)
