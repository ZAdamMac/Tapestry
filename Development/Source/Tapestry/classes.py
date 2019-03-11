"""Defines the actual operating classes for Tapestry.py. There is essentially
no executable code in this script - it's just used to hold the working classes
for tapestry.py.

Classes are to be organized by general purpose - see block comments for guidance.

"""

import bz2
import ftplib
import hashlib
import json
import multiprocessing as mp
import os
import pickle
import shutil
import tarfile

# Define Exceptions


class RecoveryIndexError(Exception):
    """Standard exception to be raised when the recovery index has an issue
    with the file it is provided."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


# Define Process and Task Classes


class ChildProcess(mp.Process):
    """A simple, logicless worker process which iterates against a queue. This
    expects to find either a callable "task" class in the queue or the value
    None, which indicates the process should exit.
    """

    def __init__(self, queue_tasking, queue_complete, working_directory, locks, debug=False):
        """Initialize the class. Must provide the queue to attach to, the
        working directory to use, and a debug flag.

        :param queue_tasking: mp.Queue object used for multiprocess communication.
        :param queue_complete: mp.Queue object used for communicating completions
        :param working_directory: String to the absolute path of the desired
        working directory.
        :param locks: a dictionary of blockname:lock pairs (optional).
        :param debug: Boolean, activates the debugging statement.
        """
        mp.Process.__init__(self)
        self.queue = queue_tasking
        self.debug = debug
        self.ret = queue_complete
        if not os.path.isdir(working_directory):
            os.mkdir(working_directory)
        os.chdir(working_directory)

        global dict_locks
        dict_locks = locks

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

    def __init__(self, tarf, fid, path, bname):
        """
        Create the tarfile or, otherwise, add a file to it.
        :param tarf: which tarfile to use, relative to the working directory
        :param fid: GUID FID as a string.
        :param path: absolute path to the file in need of backup
        :param bname: block name, used as a key to the locks dictionary.
        """
        self.tarf = tarf
        self.a = fid
        self.b = path
        self.block = bname

    def __call__(self):
        global dict_locks
        if os.path.exists(self.tarf):  # we need to know if we're starting a new file or not.
            tarf_mode = "a:"
        else:
            tarf_mode = "r:"

        f_lock = dict_locks[self.block]  # Aquires the lock indicated in the index value from the master
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
        self.tap_name += self.tap_name+".decrypted"
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


class TaskCheckIntegrity(object):
    """A task, to be completed by ChildProcess, which contains the information
    and operations needed to check the integrity of a file in the archive
    against it's known-good composition, based on the MD5 hash.
    """

    def __init__(self, tarfile, fid, hash):
        """Provided with a tarfile, an FID found within it, and a known good
        hash, returns True or False if the file matches, as well as a string
        used in debugging.

        :param tarfile: string denoting absolute path to the tarball
        :param fid: GUID file identifier of the file in question.
        :param hash: the output of md5.hexdigest(), as found (e.g) in the RIFF
        """
        self.tarf = tarfile
        self.fid = fid
        self.hash_good = hash

    def __call__(self):
        hasher = hashlib.md5()
        with tarfile.open(self.tarf, "rb") as tarball:
            file_under_test = tarball.extractfile(self.fid)
            if file_under_test is None:
                return [False, "File %s not Found" % self.fid]
            else:
                hasher.update(file_under_test.read())
        if hasher.hexdigest() == self.hash_good:
            return [True, "File %s has a valid hash." % self.fid]
        else:
            return [False, "File %s has an invalid hash." % self.fid]


# Define Package Overrides


class FTP_TLS(ftplib.FTP_TLS):  # With thanks to hynekcer
    """Explicit FTPS, with shared TLS session"""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)  # this is the fix
        return conn, size


# Define Utility Objects

class Block(object):
    """Class representation of a tapestry block object. Exposes a method "put"
    to add a file to the block, and another, "meta" method, for adding the
    full-run metadata file to a batch before proceeding with packing.

    """

    def __init__(self, name, max_size, count):
        """Initialize the block with its preset values.

        :param name: string, output filename
        :param max_size: int in bytes
        """
        self.name = name # This string will be used as the final output filename
        self.max_size = max_size
        self.size = 0
        self.file_index = {}
        self.remaining = max_size
        self.files = 0 # A simple integer counter
        self.run_metadata = {}
        self.num_block = count
        self.block_metadata = {}
        self.global_index = {}

    def put(self, file_identifier, file_index_object):
        """Accepts an arbitrary file index identifier and the corresponding
        dictionary of metadata, as from a recovery index object"""
        if file_index_object['fsize'] <= self.remaining: # the new file will fit
            self.file_index.update({file_identifier: file_index_object})
            self.size += file_index_object['fsize']
            self.files += 1
            self.remaining = self.max_size - self.size
            return True
        else: # This file won't fit and has to be placed somewhere else.
            return False

    def meta(self, sum_blocks, sum_size, sum_files, datestamp, comment_string, full_index, drop_dir):
        """Provided these arguments, populate the runMetadata portion of a RIFF,
        then create the corresponding RIFF file.
        """
        meta_value = {}
        meta_value.update({"sumBlock": sum_blocks})
        meta_value.update({"sizeExtraLarge": sum_size})
        meta_value.update({"countFilesSum": sum_files})
        meta_value.update({"dateRec": datestamp})
        if comment_string is None:
            comment_string = "No Comment"
        meta_value.update({"comment": comment_string})
        self.run_metadata = meta_value

        self.block_metadata = {
            "numBlock": self.num_block, "sizeLarge": self.size, "countFiles": self.files
        }

        self.global_index = full_index

        dict_riff = {"metaBlock": self.block_metadata, "metaRun": self.run_metadata,
                     "index": self.global_index}

        with open(os.path.join(drop_dir, self.name+".riff"), "w") as riff:
            json.dump(dict_riff, riff)

        return os.path.join(drop_dir, (self.name+".riff"))



class RecoveryIndex(object):
    """Special utility class for loading and translating Tapestry recovery
    index files and presenting them back to the script in a universal way. Made
    for both the old Recovery Pickle design as well as the NewRIFF format.
    """

    def __init__(self, index_file):
        """Initialize the Recovery Index by handing it a working file.

        :param file: a reader object containing the file in question.
        """
        self.pickle_failed = False
        self.json_failed = False

        try:
            self.pickled_data = pickle.load(index_file)
        except pickle.UnpicklingError:  # In this case we must have a newRiff:
            self.pickle_failed = True

        try:
            self.unpacked_json = json.load(index_file)
        except JSONDecodeError:
            self.json_failed = True

        if self.pickle_failed and self.json_failed:
            raise RecoveryIndexError("The recovery index is not a valid file type, or corrupt.")
        elif self.pickle_failed:
            self.mode = "json"
        else:
            self.mode = "pkl"

        if self.mode == "json":
            self.run_metadata = self.unpacked_json["metaRun"]
            self.file_index = self.unpacked_json["index"]
            self.blocks = self.unpacked_json["metaRun"]["sumBlock"]
        elif self.mode == "pkl":
            self.blocks, self.rec_paths, self.rec_sections = self.pickled_data
        else:  # We have entered a cursed state...
            raise RecoveryIndexError("The self.mode variable is an unexpected value. Are you hacking?")

        def find(file_key):
            """Expectes a FID value as the argument and will return the
            category and sub-path accordingly.

            :param file_key: A string representing a valid file ID.
            """
            if file_key.lower() in ["recovery-pkl", "recovery-riff"]:
                category = "skip"
                sub_path = "skip"
                return category, sub_path
            elif self.mode == "json":
                try:
                    category = self.file_index[file_key]["category"]
                    sub_path = self.file_index[file_key]["fpath"]
                except KeyError:
                    category = b"404"
                    sub_path = b"404"
            elif self.mode == "pkl":
                try:
                    category = self.rec_sections[file_key]
                    sub_path = self.rec_paths[file_key]
                except KeyError:
                    category = b"404"
                    sub_path = b"404"
            else:
                raise RecoveryIndexError("The self.mode variable is an unexpected value. Are you hacking?")

            return category, sub_path
