"""Tapestry is a specialized backup tool for creating full-file backup packages
and storing them under conditions where the secrecy of the storage media is not
necessarily trusted. For complete usage information refer to the readme.md in
this package, or at the development repo:

github: https://www.github.com/ZAdamMac/Tapestry

"""

from . import classes as tapestry
import argparse
from collections import namedtuple
import configparser
import datetime
import getpass
import gnupg
import hashlib
import io
import keyring
import multiprocessing as mp
import os
import paramiko.ssh_exception as sshe
import platform
import pysftp
from random import shuffle
import shutil
import sys
import tarfile
import textwrap
import uuid

__version__ = "2.1.1"

# Class Definitions


class Namespace(object):  # this just creates an object with arbitrary attributes.
    pass

# Function Definitions


def access_test(absolute_path, test_F=True, test_R=True, test_W=True, test_X=False):
    """Tests to see what access rights we have
    
    Args:
        absolute_path (os.path): Path to test against
        test_F (bool, optional): Enable os.F_OK (exist) rights test. Defaults to True.
        test_R (bool, optional): Enable os.R_OK (read) rights test. Defaults to True.
        test_W (bool, optional): Enable os.W_OK (write) rights test. Defaults to True.
        test_X (bool, optional): Enable os.X_OK (execute) rights test. Defaults to False.
    
    Returns:
        tuple: Results of each test. Attribute for tests not conducted will be None.
    """
    Result = namedtuple('AccessTestResult', ['exist', 'read', 'write', 'execute'])
    r = Result(
        os.access(absolute_path, os.F_OK) if test_F else None,
        os.access(absolute_path, os.R_OK) if test_R else None,
        os.access(absolute_path, os.W_OK) if test_W else None,
        os.access(absolute_path, os.X_OK) if test_X else None
    )
    return r


def announce():
    """Simple code for printing out the greeting on startup."""
    print("Welcome to Tapestry Backup Tool Version " + __version__)
    print("Automatic updates are not currently a function of this script.")
    print("Please refer to the repo for updates: https://www.github.com/ZAdamMac/Tapestry")
    debug_print("The current OS is: " + platform.system())


def build_ops_list(namespace):
    """A simple function which performs the crawling we need to do, and returns
    the findex of a RIFF). The returned index is not sorted by size and has to
    be sorted to do the blocksort.

    :param namespace: The namespace object, which by this point should be fully
    populated after passing through parse_config and parse_args
    :return:
    """
    ns = namespace
    ns.logs.log("Building the Operations list. A list of rejected files and their reasons follows.")
    ns.logs.log("For a list of files that were not rejected, decrypt and read the main RIFF file.")
    # Step 1: Index Everything for the Blocksort
    files_index = {}  # This comes out the same as the 'findex' key in a NewRIFF JSON
    node = uuid.getnode()
    run_list = ns.categories_default
    if ns.inc:
        for category in ns.categories_inclusive:
            run_list.append(category)
    for category in run_list:
        for dir_path, sub_dirs, files in os.walk(ns.category_paths[category]):
            for file in files:
                absolute_path = os.path.join(dir_path, file)
                sub_path = os.path.relpath(absolute_path, ns.category_paths[category])
                access_test_results = access_test(absolute_path)
                if False not in access_test_results:
                    size = os.path.getsize(absolute_path)
                    try:
                        if size <= ns.block_size_raw:  # We'll be handling this file.
                            hasher = hashlib.new('sha256')
                            with open(absolute_path, "rb") as contents:
                                chunk = contents.read(io.DEFAULT_BUFFER_SIZE)
                                while chunk != b"":
                                    hasher.update(chunk)
                                    chunk = contents.read(io.DEFAULT_BUFFER_SIZE)
                            hash_digest = hasher.hexdigest()
                            file_descriptor = {
                                'fname': file, 'sha256': hash_digest, 'category': category,
                                'fpath': sub_path, 'fsize': size
                                }
                            files_index.update({str(uuid.uuid1(node)): file_descriptor})
                        else:
                            size_pretty = size / 1048576
                            block_size_pretty = ns.block_size_raw / 1048576
                            message = ("{%s} %s is larger than %s (%s) and is being excluded" %
                                (category, file, size_pretty, block_size_pretty))
                            print(message)
                            ns.logs.log(message)
                    except PermissionError:
                        message = ("Error accessing %s: %s. Was this a network share file?"
                                   % (absolute_path, access_test_results))
                        print(message)
                        ns.logs.log(message)
                else:
                    message = ("Error accessing %s: %s. Verify it exists and you have permissions" %
                              (absolute_path, access_test_results))
                    print(message)
                    ns.logs.log(message)

    return files_index


def build_recovery_index(ops_list):
    """Provided with the output of a build_ops_list function, this function
    will return a sorted recovery index (fit for blocksort, which is contained
    in the pack_blocks function)

    :param ops_list: the "files_index" object returned by build_ops_list
    """
    dict_sizes = {}
    sum_size = 0
    for findex in ops_list.keys():
        sum_size += ops_list[findex]['fsize']
        dict_sizes.update({findex: ops_list[findex]['fsize']})

    working_index = sorted(dict_sizes, key=dict_sizes.__getitem__)
    working_index.reverse()

    return working_index, sum_size


def clean_up(working_directory):
    """Releases the memory space used up by temp, because we're polite."""
    if os.path.exists(working_directory):
        shutil.rmtree(working_directory, ignore_errors=True)


def compress_blocks(ns, targets, do_compression=True, compression_level=1):
    """Iterates over a list of files, and then compresses them, using the
    multiprocessing framework.
    :param ns: a tapestry namespace object
    :param targets: list of absolute paths to the files to be compressed.
    :param do_compression: boolean value indicting if we should use compression
    :param compression_level: integer value from 1-9 denoting the number of passes
    :return: list of absolute paths of the resulting files.
    """
    if do_compression:
        worker_count = os.cpu_count()
        compress_queue = mp.JoinableQueue()
        for target in targets:
            task = tapestry.TaskCompress(target, compression_level)
            compress_queue.put(task)
        workers = []
        sum_jobs = int(compress_queue.qsize())
        done = mp.JoinableQueue()
        for i in range(worker_count):
            workers.append(tapestry.ChildProcess(compress_queue, done, ns.workDir, ns.debug))
        rounds_complete = 0
        debug_print(str(targets)+"\n")
        for w in workers:
            w.start()
        working = True
        status_print(0, sum_jobs, "Compressing", "Working...")  # We need an initial status print
        while working:
            message = done.get()
            if message is None:
                working = False
            else:
                if not ns.debug:
                    message = "Working..."
                rounds_complete += 1
                status_print(rounds_complete, sum_jobs, "Compressing", message)
                if rounds_complete == sum_jobs:
                    done.put(None)  # Use none as a poison pill to kill the queue.
                done.task_done()
        compress_queue.join()
        for w in workers:
            compress_queue.put(None)
        replacement_list = []
        for target in targets:
            out = target+".bz2"
            replacement_list.append(out)
    else:
        replacement_list = targets
    print("\n")

    return replacement_list


def debug_print(body):
    """Checks for the value of a global variable, debug, and determines whether
    or not to print the "body" argument to stout.
    """
    output_string = str(body)
    try:
        global state
        if state.debug:
            print(output_string)
            state.logs.log(output_string)
    except NameError:  # In this edge case we are probably running in a test context
        print(output_string)  # therefore output is likely desired


def decompress_blocks(namespace):
    """Provided a namespace object, this function will crawl the defined
    working directory, looking for decrypted tap files to decompress for
    performance purposes.

    :param namespace: The system namespace object.
    :return:
    """
    ns = namespace

    found_decrypted = []  # Need to find all the decrypted blocks
    for foo, bar, files in os.walk(ns.workDir):
        for file in files:
            if file.endswith(".decrypted"):
                found_decrypted.append(os.path.join(foo, file))

    tasks = mp.JoinableQueue()  # Let's populate the queue
    for file in found_decrypted:
        tasks.put(tapestry.TaskDecompress(file))
    sum_jobs = tasks.qsize()

    workers = []
    done = mp.JoinableQueue()
    for i in range(os.cpu_count()):
        workers.append(tapestry.ChildProcess(tasks, done, ns.workDir, ns.debug))
    rounds_complete = 0
    status_print(rounds_complete, sum_jobs, "Decompressing", "Working...")
    for w in workers:
        w.start()
    working = True
    while working:
        message = done.get()
        if message is None:
            working = False
        else:
            if not ns.debug:
                message = "Working..."
            rounds_complete += 1
            status_print(rounds_complete, sum_jobs, "Decompressing", message)
            if rounds_complete == sum_jobs:
                done.put(None)  # Use none as a poison pill to kill the queue.
            done.task_done()
    tasks.join()
    for w in workers:
        tasks.put(None)
    tasks.join()


def decrypt_blocks(ns, verified_blocks, gpg_agent):
    """Iterates over the provided list of verified blocks, producing decrypted
    versions in the same directory, using the provided gpg agent. This is done
    leveraging the multiprocess package via the provided classes.py.

    :param ns: The process namespace object
    :param verified_blocks: a list of absolute file paths, ideally provided by
    tapestry.verify_blocks
    :param gpg_agent: A python-gnupg GPG object.
    :return:
    """
    worker_count = os.cpu_count()
    """It should be noted this method of obtaining the maximum number of
    processes to spawn is highly simplistic. Performance enhancements in
    Tapestry's future will likely focus around finding a more elegant way
    to do this.
    """
    tasks = mp.JoinableQueue()  # This queue provides jobs to be done.
    done = mp.JoinableQueue()  # This queue provides jobs which ARE done.
    workers = []
    for i in range(worker_count):
        workers.append(tapestry.ChildProcess(tasks, done, ns.workDir, ns.debug))
    for block in verified_blocks:
        if not os.path.exists(block+".decrypted"):  # No sense repeating
            tasks.put(tapestry.TaskDecrypt(block, ns.workDir, gpg_agent))
    sum_jobs = tasks.qsize()
    rounds_complete = 0
    for w in workers:
        w.start()
    working = True
    if sum_jobs > 0:  # This would be the case if the block fails.
        status_print(rounds_complete, sum_jobs, "Decrypting", "Working...")
        while working:
            message = done.get()
            if message is None:
                working = False
            else:
                if not ns.debug:
                    message = "Working..."
                rounds_complete += 1
                status_print(rounds_complete, sum_jobs, "Decrypting", message)
                if rounds_complete == sum_jobs:
                    done.put(None)  # Use none as a poison pill to kill the queue.
                done.task_done()
        tasks.join()
        for w in workers:
            tasks.put(None)
        tasks.join()
    else:
        print("""Skipping Decryption as the current backup was decrypted during initial preparation.""")
        for w in workers:
            tasks.put(None)
        tasks.join()


def do_main(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire build process."""
    debug_print("Entering do_main")
    ns = namespace
    print("Gathering a list of files to archive - this could take a few minutes.")
    ops_list = build_ops_list(namespace)
    debug_print("Have ops list")
    print("Sorting the files to be archived - this could take a few minutes")
    raw_recovery_index, namespace.sum_size = build_recovery_index(ops_list)
    debug_print("Have RI, Proceeding to Pack")
    if sys.platform == "win32":
        list_blocks = windows_pack_blocks(raw_recovery_index, ops_list, namespace)
    else:
        list_blocks = unix_pack_blocks(raw_recovery_index, ops_list, namespace)
    list_blocks = compress_blocks(ns, list_blocks, ns.compress, ns.compressLevel)
    prevalidate_blocks(ns, list_blocks, ops_list)
    encrypt_blocks(list_blocks, gpg_agent, ns.activeFP, ns)
    sign_blocks(namespace, gpg_agent)
    if namespace.modeNetwork.lower() == "sftp":
        sftp_deposit_files(namespace)
    clean_up(namespace.workDir)
    print("The temporary working directories have been cleared and your files")
    print("are now stored here: %s" % namespace.drop)
    ns.logs.save()
    exit(0)


def do_recovery(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire recovery process."""
    ns = namespace
    print("Entering Recovery Mode")
    ns.logs.log("This is a recovery-mode operation.")
    if ns.modeNetwork.lower() == "sftp":
        print("Fetching available blocks from the FTP server.")
        ns.logs.log("Using SFTP to retrieve backup data.")
        namespace = sftp_retrieve_files(namespace, gpg_agent)
        print("FTP Fetch Completed")
    else:
        ns.logs.log("Attempting to search %s for recovery files." % namespace.recovery_path)
        rec_index = media_retrieve_files(namespace.recovery_path, namespace.workDir,
                                         gpg_agent, ns.logs)
        namespace.rec_index = rec_index
        debug_print("DoRecovery: namespace after MRF: %s" % namespace)
    verified_blocks = verify_blocks(namespace, gpg_agent)
    decrypt_blocks(namespace, verified_blocks, gpg_agent)
    decompress_blocks(namespace)
    unpack_blocks(namespace)
    clean_up(namespace.workDir)
    debug_print("REC: Got this far, so I should terminate")
    ns.logs.save()
    exit(0)


def encrypt_blocks(targets, gpg_agent, fingerprint, namespace):
    """Does the needful to take an argued list of packaged blocks and encrypt.
    Returns a list of the output files.

    :param targets: list of target files to process
    :param gpg_agent: a python-gnupg gpg_agent object to do the encryption
    :param fingerprint: the fingerprint to encrypt the files to.
    :param namespace: the working namespace process
    :return:
    """
    ns = namespace
    out = ns.drop
    jobs = mp.JoinableQueue()
    for target in targets:
        job = tapestry.TaskEncrypt(target, fingerprint, out, gpg_agent)
        jobs.put(job)
    workers = []
    sum_jobs = int(jobs.qsize())
    done = mp.JoinableQueue()
    for i in range(os.cpu_count()):
        workers.append(tapestry.ChildProcess(jobs, done, ns.workDir, ns.debug))
    rounds_complete = 0
    for w in workers:
        w.start()
    working = True
    status_print(rounds_complete, sum_jobs, "Encrypting", "Working...")
    while working:
        message = done.get()
        if message is None:
            working = False
        if not ns.debug:
            message = "Working..."
        rounds_complete += 1
        if rounds_complete == sum_jobs:
            done.put(None)  # Use none as a poison pill to kill the queue.
        if rounds_complete <= sum_jobs:
            status_print(rounds_complete, sum_jobs, "Encrypting", message)
        done.task_done()
    jobs.join()
    for w in workers:
        jobs.put(None)
    jobs.join()


def format_table(dict_data, list_column_order, output_width):
    # Build the Larger Dictionary (for Width Data)
    expanded_dict_data = {}
    for column in dict_data:
        longest = 0
        for row in dict_data[column]:
            if len(row) > longest:
                longest = len(row)
        expanded_dict_data.update({column: {"len_max": longest, "data": dict_data[column]}})
    # Truncate all entries to maximum width
    remaining_width = int(output_width)
    divider = len(list_column_order)
    for column in list_column_order:  # This step allows for columnar compression
        if divider > 1:
            pad_r = 3
        else:
            pad_r = 0
        if expanded_dict_data[column]["len_max"] < (remaining_width / divider - pad_r):
            width = (expanded_dict_data[column]["len_max"] + pad_r)  # The column will fit with seperator, unmodified
            expanded_dict_data[column].update({"width": width})
        else:
            trimmed_data = []
            for row in expanded_dict_data[column]["data"]:
                new_row = textwrap.shorten(row, (remaining_width/divider - pad_r), placeholder="...")
                trimmed_data.append(new_row)
            expanded_dict_data[column].update({"data": trimmed_data})
            width = remaining_width / divider
            expanded_dict_data[column].update({"width": (remaining_width / divider)})
        remaining_width -= width  # We have that much room left
        divider -= 1  # And this many rows left to count.
    # Add padding to entries
    for column in list_column_order:
        pad_to = expanded_dict_data[column]["width"]
        padded_data = []
        for row in expanded_dict_data[column]["data"]:
            while len(row) < (pad_to-3):
                row += " "
            padded_data.append(row)
        expanded_dict_data[column].update({"data": padded_data})
    # Build header line/seperator
    output_array = []
    header = ""
    for column in list_column_order:
        pad_to = expanded_dict_data[column]["width"]
        while len(column) < pad_to:
            column += " "
        header += column
    output_array.append(header)
    seperator = ""
    while len(seperator) < output_width:
        seperator += "-"
    output_array.append(seperator)
    # Build each line
    sum_rows = len(expanded_dict_data[list_column_order[0]]["data"])
    for row in range(sum_rows):
        this_row = ""
        for column in list_column_order:
            this_row += " | " + expanded_dict_data[column]["data"][row]
        this_row = this_row.lstrip(" | ")
        output_array.append(this_row)

    return output_array


def generate_keys(namespace, gpg_agent):
    """Provided with a namespace and a connection to the gpg agent, generates a
    new key. Does not obviate the build runtime.
    """
    namespace.logs.log("The --genKey flag was set, so a new key needed to be generated.")
    print("You have indicated you wish to have Tapestry generate a new Disaster Recovery Key.")
    print(("This key will be a %s -bit RSA Key Pair with the credentials you specify." % namespace.keysize))
    print("This key will not expire by default. If you need this functionality, add it in GPG.")
    name_key = str(input("User/Organization Name: "))
    contact_key = str(input("Recovery Contact Email: "))
    print("You will be prompted externally to enter a passphrase for this key via your default pinentry program.")
    inp = gpg_agent.gen_key_input(key_type="RSA", key_length=namespace.keysize,
                                  name_real=name_key, name_comment="Tapestry Recovery",
                                  name_email=contact_key)
    keypair = gpg_agent.gen_key(inp)
    namespace.activeFP = keypair.fingerprint  # Changes the value of FP to the new key
    namespace.logs.log(("The newly-generated key's fingerprint was %s" % keypair.fingerprint))

    config = configparser.ConfigParser()

    if os.path.exists(namespace.config_path):
        config.read(namespace.config_path)
    config.set("Environment Variables", "Expected FP", str(namespace.activeFP))  # sets this value in config
    namespace.activeFP = keypair.fingerprint
    with open(namespace.config_path, "w") as cf:
        config.write(cf)

    if not os.path.isdir(namespace.drop):
        os.mkdir(namespace.drop)
    os.chdir(namespace.drop)
    pub_out = gpg_agent.export_keys(namespace.activeFP)
    pub_file = os.open("DRPub.key", os.O_CREAT | os.O_RDWR)
    pub_handle = os.fdopen(pub_file, "w")
    pub_handle.write(str(pub_out))
    pub_handle.close()
    try:
        key_out = gpg_agent.export_keys(namespace.activeFP, True, expect_passphrase=False)
        key_file = os.open("DR.key", os.O_CREAT | os.O_RDWR)
        key_handle = os.fdopen(key_file, "w")
        key_handle.write(str(key_out))
        key_handle.close()
        print("The new keys have been saved in the output folder. Please move them to removable media or other backup.")
    except ValueError:  # Most Probable cause for this is that the version of the gnupg module is outdated
        print("An error has occured which prevented the private side of the disaster recovery key from being exported.")
        print("This error is likely caused by this system's version of the python-gnupg module being outdated.")
        print("You can export the key manually using the method of your choice.")
        namespace.logs.log("An error prevented the keys from being exported - this usually has to do with"
                           " this machine's version of python-gnupg being outdated. You can update this with "
                           "pip.")

    return namespace


def keyring_get_value(key, strict=True):
    """    Aconvenience wrapper that attempts to get a value stored in the keyring's 'tapestry' system based on input
    string "key". If it fails to find a value for key while kwarg strict=True, it will raise KeyError.
    """
    value = keyring.get_password("tapestry", key)
    if strict:
        if value is None:
            raise KeyError
    return value


def get_user_input(message, dict_data, resp_column, list_column_order):
    # get the size of the terminal window
    width, height = shutil.get_terminal_size((80, 24))
    # make an index to add to the dict_data
    list_pass_columns = ["index"]
    for column in list_column_order: # Todo did this ever work? Is this untested?
        list_pass_columns.append()
    index = []
    counter = 1
    for each in dict_data[0]:
        index.append(counter)
        counter += 1
    dict_data.update({"index": index})
    # pretty-print the message.
    for each in textwrap.wrap(message, width=width):
        print(each)
    # Drop to the table printer.
    for each in format_table(dict_data, list_column_order, width):
        print(each)
    # Get response
    response = input("Enter the row number of your selection: ")
    response = (int(response)-1)  # Drop to a real index.
    # Return looked-up value
    lookup_list = dict_data[resp_column]
    return lookup_list[response]


def media_retrieve_files(mountpoint, temp_path, gpg_agent, logs):
    """Iterates over mountpoint, moving .tap files and their signatures to the
    temporary working directory. Early in operation, will retrieve the recovery
    pickle or NewRIFF index from the first block it finds.

    :param mountpoint: absolute path to the media mountpoint.
    :param temp_path: absolute path to the system's working directory.
    :param gpg_agent: a python-gnupg gpg agent object
    :param logs: ns.logs, the SimpleLogger object.
    :return:
    """
    print("Now searching local media for the first block. This includes decrypting")
    print("the first block in order to obtain the recovery index. Please wait.")
    found_blocks = []
    found_sigs = []
    initial_block_hunt = True

    while initial_block_hunt:
        for location, sub_directories, files in os.walk(mountpoint):
            debug_print("media_retrieve_files' mountpoint is: %s" % mountpoint)
            if not os.path.exists(temp_path):  # We must create this explicitly for shutil
                os.mkdir(temp_path)
            for file in files:
                if file.endswith(".tap"):
                    found_blocks.append(file)
                    shutil.copy(os.path.join(location, file), os.path.join(temp_path, file))
                elif file.endswith(".tap.sig"):
                    found_sigs.append(file)
                    shutil.copy(os.path.join(location, file), os.path.join(temp_path, file))

        if len(found_blocks) == 0:
            print("The are no recovery files on the mountpoint at %s" % mountpoint)
            print("Check the media is inserted correctly (or that that address is correct) and try again.")
            input("Press enter to continue")
            logs.log("Didn't find files there, retrying. If the log ends here the user aborted the recovery.")
        else:
            initial_block_hunt = False

    # Now we need to obtain a recovery file of some kind.
    decrypted_first = tapestry.TaskDecrypt(os.path.join(temp_path, found_blocks[0]), temp_path, gpg_agent)
    decrypted_first = decrypted_first()
    debug_print("MRF: decrypted_first is: %s" % decrypted_first)
    debug_print("MRF: The conditional is therefore: %s" % decrypted_first.split(" ")[1].lower())
    if decrypted_first.split(" ")[1].lower() == "success":
        tar = tarfile.open(os.path.join(temp_path, decrypted_first.split(" ")[3].rstrip(".")), "r:*")
        # Hideous string management hack.
        tapfile_contents = tar.getnames()
        debug_print("The provided block contains: %s" % str(tapfile_contents))

        if "recovery-pkl" in tapfile_contents:
            index_file = tar.extractfile("recovery-pkl")
        elif "recovery-riff" in tapfile_contents:
            index_file = tar.extractfile("recovery-riff")
        else:
            index_file = open("/dev/null", "rb")  # Just for giggles
            print("Something has gone wrong!")
            print("One or more blocks are corrupt and missing their recovery index.")
            print("This is a fatal error.")
            logs.log("FATAL ERROR: One or more blocks has a corrupted index. The program will now terminate.")
            exit(1)
    else:
        print("Something has gone wrong in initial decryption.")
        print("Verify you have the key for the blocks provided and try again.")
        logs.log("FATAL ERROR: The user's keyring did not have the correct key for these blocks.")
        exit(2)

    # If we made it this far, we have a recovery file, so let's return a recovery index
    rec_index = tapestry.RecoveryIndex(index_file)

    while len(found_blocks) < rec_index.blocks:
        print("One or more blocks are missing. Please insert the next disk")
        input("Press enter to continue")
        for location, sub_directories, files in os.walk(mountpoint):
            for file in files:
                if file.endswith(".tap"):
                    found_blocks.append(file)
                    shutil.copy(file, os.path.join(temp_path, file))
                elif file.endswith(".tap.sig"):
                    found_sigs.append(file)
                    shutil.copy(file, os.path.join(temp_path, file))

    return rec_index


def unix_pack_blocks(sizes, ops_list, namespace):
    """Processes files by creating the individual tarred tapblock files, and
    returns a list of those files and their absolute paths to be processed by
    the next stage of events. This version is specific to unix systems (defined
    as all non-windows systems in this case) and uses the multiprocessing
    module to gain about a 20% performance increase on average compared to the
    windows version.

    :param sizes: a list object returned by build_recovery_index, made up of
    strings indicating file identifier values sorted by the size of the file.
    :param ops_list: The full ops list prepared by build_ops_list, which is
    equivalent to the third portion of a recovery index file.
    :param namespace: the entire namespace object.
    :return:
    """
    ns = namespace
    collection_blocks = []
    block_final_paths = []
    block_name_base = ns.compid+"-"+str(datetime.date.today())
    counter = 1  # Remember to increment this later
    smallest = ops_list[sizes[-1]]['fsize']
    working_block = tapestry.Block(
        (block_name_base+"-"+str(counter)), ns.block_size_raw, counter, smallest
    )
    packing = True
    while packing:
        placed_items = []
        for item in sizes:
            placed = working_block.put(item, ops_list[item])
            if placed:
                placed_items.append(item)
        for placed_item in placed_items:  # We need to do this rather than popping them immediately
            sizes.remove(placed_item)     # Because that would break the indexing, and you still get recursion.
        if smallest == 0:  # Special edge case, causes infinite loops if true after the first run through the list.
            new_smallest = ops_list[sizes[-1]]['fsize']
            if new_smallest == 0:  # This in theory should be unreachable code but we need to account for this case.
                print("Fatal Error: Infinite Recursion in block build algorithm.")
                exit(7)
            else:
                working_block.full = True  # at this point this must necessarily be true
        if working_block.full:  # We need a new block, unpacked items.
            collection_blocks.append(working_block)
            counter += 1
            smallest = ops_list[sizes[-1]]['fsize']  # There is a new smallest file, and we need to start over.
            working_block = tapestry.Block(
                (block_name_base+"-"+str(counter)), ns.block_size_raw, counter, smallest
            )
        elif len(sizes) == 0:
            collection_blocks.append(working_block)
            packing = False  # The list is empty and we're therefore done.
    tarf_queue = mp.JoinableQueue()
    locks = {}
    temp_queue = []  # We need a temporary queue to avoid having the blocks all lined up.
    sum_files = 0
    for block in collection_blocks:
        sum_files += block.files
    sum_sizes = ns.sum_size
    for block in collection_blocks:
        this_block_lock = mp.Lock()
        locks.update({block.name: this_block_lock})
        tarf = os.path.join(ns.workDir, (block.name+".tar"))
        block_final_paths.append(tarf)
        for fid, file_metadata in block.file_index.items():
            path = os.path.join(ns.category_paths[file_metadata["category"]],
                                file_metadata['fpath'])
            this_task = tapestry.TaskTarBuild(tarf, fid, path, block.name)
            temp_queue.append(this_task)
        this_riff = block.meta(len(collection_blocks), sum_sizes, sum_files,
                               str(datetime.date.today()), ns.comment_string, ops_list, ns.drop)
        this_task = tapestry.TaskTarBuild(tarf, "recovery-riff",
                                          this_riff, block.name)
        tarf_queue.put(this_task)
    shuffle(temp_queue)  # Shuffling these tasks before feeding them into the queue is actually a speed boost.
    for task in temp_queue:
        tarf_queue.put(task)
    sum_jobs = int(tarf_queue.qsize())
    done = mp.JoinableQueue()
    workers = []
    for i in range(os.cpu_count()):
        workers.append(tapestry.ChildProcess(tarf_queue, done, ns.workDir, locks, ns.debug))
    rounds_complete = 0
    for w in workers:
        w.start()
    working = True
    while working:
        message = done.get()
        if message is None:
            working = False
        else:
            if not namespace.debug:
                message = "Working..."
            rounds_complete += 1
            status_print(rounds_complete, sum_jobs, "Packing", message)
            if rounds_complete == sum_jobs:
                done.put(None)  # Use none as a poison pill to kill the queue.
            done.task_done()
    tarf_queue.join()
    for w in workers:
        tarf_queue.put(None)

    return block_final_paths


def parse_args(namespace):
    """Parse arguments and return the modified namespace object"""
    ns = namespace
    parser = argparse.ArgumentParser(description="""
    Automatically backup or restore personal files from the system. 
    \n Full documentation at https://github.com/ZAdamMac/Tapestry/blob/master/DOCUMENTATION.md
                                    """)
    parser.add_argument('--rcv', help="Recover a previous archive from disk.",
                        action="store_true")
    parser.add_argument('--inc', help="Tells the system to include non-default sections in the backup process.",
                        action="store_true")
    parser.add_argument('--debug', help="Increase output verbosity.", action="store_true")
    parser.add_argument('--genKey', help="Generates a new key before proceeding with any other functions called.",
                        action="store_true")
    parser.add_argument('--devtest', help="Starts testing mode, see documentation", action="store_true")
    parser.add_argument('-c', help="absolute or relative path to the config file", action="store")
    parser.add_argument('--validate', help="Expects a path or csv string of paths describing blocks to validate.",
                        action="store")
    parser.add_argument('--secrets', help="Runs a subroutine to update the values of secrets in the keyring",
                                         action="store_true")
    parser.add_argument('-n', help="note to add to the metadata for this run for your future reference",
                        action='store', default=None)
    args = parser.parse_args()

    ns.rcv = args.rcv
    ns.inc = args.inc
    ns.debug = args.debug
    ns.devtest = args.devtest
    ns.genKey = args.genKey
    ns.config_path = args.c
    ns.validation_target = args.validate
    ns.secrets = args.secrets
    ns.comment_string = args.n
    if ns.validation_target is not None:
        ns.demand_validate = True
    else:
        ns.demand_validate = False

    return ns


def windows_pack_blocks(sizes, ops_list, namespace):
    """Processes files by creating the individual tarred tapblock files, and
    returns a list of those files and their absolute paths to be processed by
    the next stage of events. This version is meant to be used when the
    detected operating system is windows (sys.platform == "win32"). This runs
    in a single-process workflow because we've yet to implement an operating
    locking method under windows.

    :param sizes: a list object returned by build_recovery_index, made up of
    strings indicating file identifier values sorted by the size of the file.
    :param ops_list: The full ops list prepared by build_ops_list, which is
    equivalent to the third portion of a recovery index file.
    :param namespace: the entire namespace object.
    :return:
    """
    ns = namespace
    collection_blocks = []
    block_final_paths = []
    block_name_base = ns.compid + "-" + str(datetime.date.today())
    counter = 1  # Remember to increment this later
    smallest = ops_list[sizes[-1]]['fsize']
    working_block = tapestry.Block(
        (block_name_base + "-" + str(counter)), ns.block_size_raw, counter, smallest
    )
    if not os.path.exists(ns.workDir):
        os.mkdir(ns.workDir)

    packing = True
    while packing:
        placed_items = []
        for item in sizes:
            placed = working_block.put(item, ops_list[item])
            if placed:
                placed_items.append(item)
        for placed_item in placed_items:  # We need to do this rather than popping them immediately
            sizes.remove(placed_item)     # Because that would break the indexing, and you still get recursion.
        if smallest == 0:  # Special edge case, causes infinite loops if true after the first run through the list.
            new_smallest = ops_list[sizes[-1]]['fsize']
            if new_smallest == 0:  # This in theory should be unreachable code but we need to account for this case.
                print("Fatal Error: Infinite Recursion in block build algorithm.")
                exit(7)
            else:
                working_block.full = True  # at this point this must necessarily be true
        if working_block.full:  # We need a new block, unpacked items.
            collection_blocks.append(working_block)
            counter += 1
            working_block = tapestry.Block(
                (block_name_base + "-" + str(counter)), ns.block_size_raw, counter, smallest
            )
        elif len(sizes) == 0:
            collection_blocks.append(working_block)
            packing = False  # The list is empty and we're therefore done.
    sum_files = 0
    for block in collection_blocks:
        sum_files += block.files
    sum_sizes = ns.sum_size
    current_counter = 0
    for block in collection_blocks:
        tarf = os.path.join(ns.workDir, (block.name + ".tar"))
        block_final_paths.append(tarf)
        for fid, file_metadata in block.file_index.items():
            current_counter += 1
            path = os.path.join(ns.category_paths[file_metadata["category"]],
                                file_metadata['fpath'])
            with tarfile.open(tarf, "a:") as tf:
                tf.add(path, arcname=fid, recursive=False)
            status_print(current_counter, sum_files, "Packing", None)
        this_riff = block.meta(len(collection_blocks), sum_sizes, sum_files,
                               str(datetime.date.today()), ns.comment_string, ops_list, ns.drop)
        with tarfile.open(tarf, "a:") as tf:
            tf.add(this_riff, arcname="recovery-riff", recursive=False)

    return block_final_paths


def parse_config(namespace):
    """mounts the configparser instance, grabs the config file, and passes its
    values into the namespace.
    """
    ns = namespace
    ns.currentOS = platform.system()

    config = configparser.ConfigParser()

    if not ns.config_path:  # We need a default config file name to avoid some errors.
        ns.config_path = "tapestry.cfg"

    if os.path.exists(ns.config_path):
        config.read(ns.config_path)
    else:
        print("The indicated config file: %s cannot be found." % ns.config_path)
        print("Generating a template config file in that location.")
        print("Please edit this config file appropriately and rerun the program.")
        place_config_template(ns.config_path)
        exit(3)

    try:
        ns.activeFP = config.get("Environment Variables", "Expected FP")
        ns.fp = config.get("Environment Variables", "Expected FP")
        ns.signing = config.getboolean("Environment Variables", "Sign by Default", fallback=True)
        ns.sigFP = config.get("Environment Variables", "Signing FP")
        ns.keysize = config.getint("Environment Variables", "keysize", fallback=4096)
        ns.compress = config.getboolean("Environment Variables", "Use Compression", fallback=True)
        ns.compressLevel = config.getint("Environment Variables", "Compression Level", fallback=False)
        ns.step = "none"
        ns.sumJobs = 0
        ns.jobsDone = 0
        ns.modeNetwork = config.get("Network Configuration", "mode", fallback="none")
        ns.addrNet = config.get("Network Configuration", "server", fallback=None)
        ns.portNet = config.getint("Network Configuration", "port", fallback=None)
        ns.nameNet = config.get("Network Configuration", "username", fallback=None)
        ns.network_credential_type = config.get("Network Configuration", "Auth Type", fallback=None)
        ns.network_credential_value = config.get("Network Configuration", "Credential Path", fallback=None)
        ns.network_credential_pass = config.getboolean("Network Configuration", "Credential Has Passphrase", fallback=None)
        if ns.network_credential_type.lower() == "passphrase":
            ns.network_credential_value = keyring_get_value("network_passphrase")
        if ns.network_credential_pass:
            ns.network_credential_value = keyring_get_value("network_passphrase")
        if ns.rcv:
            ns.encryption_key_passphrase = keyring_get_value("decryption_passphrase", strict=False)
        ns.signing_key_passphrase = keyring_get_value("signing_passphrase", strict=False)
        ns.dirNet = config.get("Network Configuration", "remote drop location", fallback=None)
        ns.retainLocal = config.getboolean("Network Configuration", "Keep Local Copies", fallback=True)
        ns.block_size_raw = config.getint("Environment Variables", "blockSize", fallback=2000) * (
            2 ** 20)  # The math is necessary to go from MB to Bytes
        ns.compid = config.get("Environment Variables", "compid", fallback="Tapestry")
        ns.recovery_path = config.get("Environment Variables", "recovery path", fallback=None)
        ns.uid = config.get("Environment Variables", "uid")
        ns.drop = config.get("Environment Variables", "Output Path", fallback=None)
        ns.do_validation = config.getboolean("Environment Variables", "Build-Time File Validation", fallback=True)
    except configparser.NoOptionError:
        print("Tapestry has attempted to reference a required option which is missing from the config file.")
        print("Please confirm the structure of your config file is correct.")
        print("If you have just upgraded to 2.2 or later, you may be missing added fields.")
        exit(3)
    except KeyError:
        print("Tapestry was unable to find a value it expected in the keyring for config flag %s.")
        print("Please rerun tapestry with the flag --secrets specified to adjust these values.")
        exit(6)

    if ns.currentOS == "Linux":
        ns.workDir = "/tmp/Tapestry/"
        ns.desktop = str("/home/" + ns.uid + "/Desktop")
        ns.gpgDir = str("/home/" + ns.uid + "/.gnupg")
    elif ns.currentOS == "Windows":
        ns.workDir = "C:\\users\\" + ns.uid + "\\appdata\\local\\temp\\tapestry"
        ns.desktop = str("C:\\Users\\" + ns.uid + "\\Desktop")
        ns.gpgDir = "C:\\users\\" + ns.uid + "\\appdata\\roaming\\gnupg"
    ns.numConsumers = os.cpu_count()
    debug_print("I am operating with %s consumers." % ns.numConsumers)

    # lastly, now that we know current OS, let's build the dictionary of categories
    ns.category_paths = {}
    ns.categories_default = []
    ns.categories_inclusive = []  # May be Inc or Default
    if ns.currentOS == "Linux":
        relevant = "Default Locations/Nix"
    else:
        relevant = "Default Locations/Windows"
    for category in config.options(relevant):
        category_path = config.get(relevant, category)
        ns.category_paths.update({category: category_path})
        ns.categories_default.append(category)
    if ns.currentOS == "Linux":
        relevant = "Additional Locations/Nix"
    else:
        relevant = "Additional Locations/Windows"
    for category in config.options(relevant):
        category_path = config.get(relevant, category)
        ns.category_paths.update({category: category_path})
        ns.categories_inclusive.append(category)

    return ns


def place_config_template(path):
    """Uses the default configuration dictionary to create a default config file
    at the argued location. If used as part of tapestry this triggers when
    parse_config cannot find the argued or default config file, and the script
    exits as the next action after execution.

    :param path: a string pointing to a valid path on the system
    :return:
    """

    # Note Bene: When adding to dict_default_config, values MUST BE strings, regardless of how they are
    # used later on in the routine.
    dict_default_config = {
        "Environment Variables": {
            "uid": "your_uid",
            "compid": "your_hostname",
            "blocksize": "4096",
            "expected FP": "Provide Encryption Key Fingerprint or run with option --genKey",
            "sign by default": "True",
            "signing FP": "Provide signing key fingerprint",
            "recovery path": "Provide path to the recovery file location, ex. /media/ or D:/",
            "output path": "Provide path to the output for recovery file and logs.",
            "keysize": "2048",
            "use compression": "True",
            "compression level": "2",
            "Build-Time File Validation": "True"
        },
        "Network Configuration": {
            "mode": "none",
            "server": "localhost",
            "port": "21",
            "username": "ftptest",
            "remote drop location": "path on the ftp to which to drop files",
            "keep local copies": "True",
            "Auth Type": "key",
            "Credential Path": "~/.ssh/id_rsa",
            "Credential Has Passphrase": "True"
        },
        "Default Locations/Nix": {
            "category": "path to top directory, reproduce as desired."
        },
        "Default Locations/Win": {
            "category": "path to top directory, reproduce as desired."
        },
        "Additional Locations/Nix": {
            "category": "path to top directory, reproduce as desired."
        },
        "Additional Locations/Win": {
            "category": "path to top directory, reproduce as desired."
        }
    }
    config = configparser.ConfigParser()

    for section in dict_default_config:
        options = dict_default_config[section]
        config.add_section(section)
        for option in options:
            value = options[option]
            config.set(section, option, value)

    with open(path, "w") as file_config:
        config.write(file_config)


def sign_blocks(namespace, gpg_agent):
    """Locates and signs tapestry blocks.

    :param namespace: A namespace object
    :param gpg_agent: the python-gnupg GPG agent
    :return:
    """
    ns = namespace
    out = ns.drop
    jobs = mp.JoinableQueue()
    for root, bar, files in os.walk(namespace.drop):
        debug_print(str(files)+"\n")
        for file in files:
            if file.endswith(".tap"):
                target = os.path.join(root, file)
                job = tapestry.TaskSign(target, ns.sigFP, out, gpg_agent)
                jobs.put(job)
    workers = []
    sum_jobs = int(jobs.qsize())
    debug_print(sum_jobs)
    done = mp.JoinableQueue()
    for i in range(os.cpu_count()):
        workers.append(tapestry.ChildProcess(jobs, done, ns.workDir, ns.debug))
    rounds_complete = 0
    for w in workers:
        w.start()
    working = True
    status_print(rounds_complete, sum_jobs, "Signing", "Working...")
    while working:
        message = done.get()
        if message is None:
            working = False
        if not ns.debug:
            message = "Working..."
        rounds_complete += 1
        if rounds_complete == sum_jobs:
            done.put(None)  # Use none as a poison pill to kill the queue.
        if rounds_complete <= sum_jobs:  # Patches the 200% bug.
            status_print(rounds_complete, sum_jobs, "Signing", message)
        done.task_done()
    jobs.join()
    for w in workers:
        jobs.put(None)
    jobs.join()


def start_gpg(ns):
    """Starts the GPG handler based on the current state. If --devtest or
    --debug were passed at runtime, the gpg handler will be verbose.
    """
    verbose = False
    if ns.debug or ns.devtest:
        verbose = True
    gpg = gnupg.GPG(gnupghome=ns.gpgDir, verbose=verbose)

    return gpg


def status_print(done, total, job, message):
    """Prints a basic status message. If not interrupted, prints it on one line"""
    length_bar = 15.0
    done_bar = int(round((done / total) * length_bar))
    done_bar_print = str("#" * int(done_bar) + "-" * int(round((length_bar - done_bar))))
    percent = int(round((done / total) * 100))
    if percent == 100:  # More Pretty Printing!
        if message == "Working...":
            message = "Done!    \n"
    text = ("\r {0}: [{1}] {2}% - {3}".format(job, done_bar_print, percent, message))
    sys.stdout.write(text)
    sys.stdout.flush()


def unpack_blocks(namespace):
    """Provided a namespace object, this function will crawl the defined
    working directory, looking for decrypted tap files to unpack into their
    destinations according to the recovered index.

    :param namespace: The system namespace object.
    :return:
    """
    ns = namespace

    found_decrypted = []  # Need to find all the decrypted blocks
    for foo, bar, files in os.walk(ns.workDir):
        for file in files:
            if file.endswith(".decrypted"):
                found_decrypted.append(file)

    files_to_unpack = {}  # Now we need to iterate over each of those blocks for files
    for block in found_decrypted:
        with tarfile.open(block, "r:*") as tap:
            members = tap.getnames()
            for file in members:
                # debug_print("UB: Trying to unblock %s" % str({file: block}))
                files_to_unpack.update({file: block})

    tasks = mp.JoinableQueue()  # Let's populate the queue
    for file in files_to_unpack:
        skip = False
        category_label, sub_path = ns.rec_index.find(file)
        if category_label == b"404":
            skip = True
        elif category_label == "skip":
            skip = True
        try:
            category_dir = ns.category_paths[category_label]
        except KeyError:
            category_dir = os.path.join(ns.drop, str(category_label))
            # Because cat_label sometimes comes back as b"404", we need to smash it back to strings.
        if not skip:
            tap_absolute = os.path.join(ns.workDir, files_to_unpack[file])
            tasks.put(tapestry.TaskTarUnpack(tap_absolute, file, category_dir, sub_path))
    sum_jobs = tasks.qsize()

    workers = []
    done = mp.JoinableQueue()
    for i in range(os.cpu_count()):
        workers.append(tapestry.ChildProcess(tasks, done, ns.workDir, ns.debug))
    rounds_complete = 0
    status_print(rounds_complete, sum_jobs, "Unpacking", "Working...")
    for w in workers:
        w.start()
    working = True
    while working:
        message = done.get()
        if message is None:
            working = False
        else:
            if not ns.debug:
                message = "Working..."
            rounds_complete += 1
            status_print(rounds_complete, sum_jobs, "Unpacking", message)
            if rounds_complete >= sum_jobs:
                done.put(None)  # Use none as a poison pill to kill the queue.
            done.task_done()
    tasks.join()
    for w in workers:
        tasks.put(None)
    tasks.join()


def update_secrets():
    print("You have selected --secrets, and we will now go through the possible secret values to encode them.")
    print("Secrets stored in this way are stored in your system keyring and not the tapestry system files.")
    print("Python will have access to these fields! If a secret value is not desired to be stored, press enter to skip")
    print("A blank value will delete the current stored value for that key for security reasons.")
    print("Check the documentation to see how each value is used.")
    secret_keys = ["network_passphrase", "signing_passphrase", "decryption_passphrase"]
    for each in secret_keys:
        value = getpass.getpass(prompt="%s?" % each)
        keyring.set_password("tapestry", each, value)


def verify_blocks(ns, gpg_agent, testing=False):
    """Verifies blocks and returns a list of verified blocks as a result"""
    gpg = gpg_agent
    debug_print("VB: We think that ns = %s" % ns)
    found_blocks = []
    approved_fingerprints = []
    valid_blocks = []
    for root, bar, files in os.walk(ns.workDir):
        for file in files:
            if file.endswith(".tap"):
                found_blocks.append(os.path.join(root, file))
    for block in found_blocks:
        with open(block+".sig", "rb") as k:
            result = gpg.verify_file(k, block)
        if not result.valid:
            print("Rejecting %s; invalid signature." % (os.path.split(block)[1]))
        else:
            fingerprint = result.fingerprint
            if fingerprint in approved_fingerprints:
                valid_blocks.append(block)
            else:
                print("This fingerprint requires approval: %s" % fingerprint)
                print("The fingerprint claims to be for: %s" % result.username)
                print("Compare to a known-good fingerprint for this user.")
                if not testing:
                    resume = input("Approve this fingerprint? (y/n)")
                else:
                    resume = "y"
                if "y" in resume.lower():
                    valid_blocks.append(block)
                    approved_fingerprints.append(fingerprint)

    debug_print("VB: We've verified the following blocks: %s" % valid_blocks)
    return valid_blocks


def verify_keys(ns, gpg):
    """Verify that the keys intended for use are present."""
    keys = gpg.list_keys(keys=ns.fp)
    found = False
    try:
        location = keys.key_map[ns.fp]  # If the key is in the dictionary, hooray!
        if location is not None:
            found = True
    except KeyError:
        pass
    if found is False:
        print('''Unable to locate the key with fingerprint "%s"''' % ns.activeFP)
        print("This could be due to either a configuration error, or the key needs to be re-imported.")
        print("Please double-check your configuration and keyring and try again.")
        clean_up(ns.workDir)
        exit(4)
    debug_print("Fetching key %s from Keyring" % ns.activeFP)
    debug_print(ns.activeFP)


def runtime():
    global state
    keyring.get_keyring()
    state = Namespace()
    state = parse_args(state)
    if state.secrets:
        update_secrets()
        exit(0)
    state = parse_config(state)
    state = start_logging(state)
    gpg_conn = start_gpg(state)
    announce()
    if state.modeNetwork.lower() != "none":
        if (state.network_credential_pass or (state.network_credential_type == "passphrase"))\
                and state.network_credential_value is None:
            print("Tapestry is running in network storage mode and requires some credentialing information.")
            state.network_credential_pass = getpass.getpass(prompt="Enter Network Credential Passphrase: ")
    if state.demand_validate:
        demand_validate(state, gpg_conn)
        exit(0)  # We have nothing else to do, so exit.
    if state.genKey:
        state = generate_keys(state, gpg_conn)
    verify_keys(state, gpg_conn)
    if state.rcv:
        do_recovery(state, gpg_conn)
    else:
        do_main(state, gpg_conn)
    clean_up(state.workDir)
    exit(0)


def start_logging(ns):
    """Now that we have a logger, we need a way to instantiate it and attach it
    to the namespace/state object. Fortunately, that's straight forward.

    :param ns: the namespace object to which the logger will be attached.
    :return: the modified namespace object.
    """
    date = str(datetime.date.today())
    name_logfile = "tapestry-%s.log" % date
    ns.logs = tapestry.SimpleLogger(ns.drop, name_logfile, ns.compid, date, ns.config_path)

    return ns


def sftp_connect(namespace):
    """Attempts to grab a pysftp.Connection() object for the relevant
    config information stored in tapestry.cfg. In the event of any failures the
    exceptions will be handled and reraised - the control logic should handle
    those cases with a graceful exit.

    Attaches the connection to the namespace object before returning it.

    :param namespace:
    :return: Connection (or None, if error), error (string)
    """
    ns = namespace
    error = None

    if ns.currentOS.lower() == "linux":
        user_khp = os.path.expanduser("~/.ssh/known_hosts")
        sys_khp = "/etc/ssh/known_hosts"
    elif ns.currentOS.lower() == "windows":
        user_khp = os.path.join(os.environ["USERPROFILE"], ".ssh\\known_hosts")
        sys_khp = "C:\\Windows\\System32\\config\\systemprofile\\ssh\\known_hosts"
    # First, find some known-hosts files (important for security)
    if os.path.exists(user_khp):
        cnopts = pysftp.CnOpts(knownhosts=user_khp)
    elif os.path.exists(sys_khp):
        cnopts = pysftp.CnOpts(knownhosts=sys_khp)
    else:
        # Exit with error; retain local files
        error = "Tapestry was unable to find the appropriate known_hosts file to certify the SSH connection."
        return None, error
    # Determine credential situation
    # Also, wrapped this whole block in a giant Try case to handle the possible connection failures en bloc
    try:
        sftp_connection = None
        if ns.network_credential_type.lower() == "passphrase":
           sftp_connection = pysftp.Connection(host=ns.addrNet, username=ns.nameNet, port=int(ns.portNet),
                                                   password=ns.network_credential_value)
        elif ns.network_credential_type.lower() == "key":
            if not ns.network_credential_pass:
                sftp_connection = pysftp.Connection(host=ns.addrNet, username=ns.nameNet, port=int(ns.portNet),
                                                       private_key=ns.network_credential_value)
            else:
                sftp_connection = pysftp.Connection(host=ns.addrNet, username=ns.nameNet, port=int(ns.portNet),
                                                       private_key=ns.network_credential_value,
                                                       private_key_pass=ns.network_credential_pass)
        else:
            error = "The configuration has specified an impossible or unrecognized SFTP connection type."
            sftp_connection = None
    except (sshe.AuthenticationException, sshe.PartialAuthentication) as e:
        error = "There was an error in authentication, aborting connection."
    except sshe.BadAuthenticationType as e:
        error = ("The authentication method attempted does not match which was expected by the server. "
                 "Expected: %s, attempted %s" % (e.allowed_types, ns.network_credential_type))
    except sshe.PasswordRequiredException as e:
        error = "The private key indicated requires a passphrase, which was not provided."
    except (sshe.ChannelException, sshe.NoValidConnectionsError, sshe.ProxyCommandFailure, sshe.SSHException):
        error = "Could not connect to the remote SFTP host. Retaining local files and shutting down."
    finally:
        if not sftp_connection:
            sftp_connection = None

    return sftp_connection, error


def sftp_deposit_files(namespace):
    """The function is the glue logic for transferring files to the sftp
    server while operating in that mode. This function also handles any errors
    that can be raised by the child functions and exits gracefully as needed.

    :param namespace:
    :return:
    """
    ns = namespace  # For Brevity
    allowed_files = ["tap", "sig", "riff"]  # We don't need to or want to send just anything.

    conn, error = sftp_connect(ns)

    if error:
        print("Tapestry has encountered an error with the SFTP connection and is exiting.")
        print("Your files will be retained locally.")
        print("Error: %s" % error)
        ns.logs.log("The following error arose during SFTP setup, and was fatal: \n %s" % error)
        ns.logs.save()
        clean_up(ns.workDir)
        exit(5)

    for cwd, dirs, files in os.walk(ns.drop):
        for file in files:
            fname, suffix = file.split(".")
            if suffix in allowed_files:
                sending = os.path.join(cwd, file)
                error = sftp_place(conn, sending, ns.dirNet)
                if error:
                    print(error)
                    ns.logs.log("SFTP Error: %s during delivery of %s" % (error, file))
                    if not ns.retainLocal:
                        print("Switching to local retention for this and future files.")
                        ns.logs.log("Because of the above-stated error, backup files will be retained locally.")
                        ns.retainLocal = True
                if not ns.retainLocal:
                    os.remove(sending)


def sftp_fetch(connection, remote_path, tgt, work_path):
    try:
        if connection.pwd != remote_path:
            connection.chdir(remote_path)
    except IOError:
        error = "Couldn't retrieve file from %s; no such directory on remote host" % remote_path
        return error
    try:
        connection.get(tgt, localpath=os.path.join(work_path, tgt))
    except IOError:
        error = "Couldn't retrieve %s from remote host; no such file in %s" % (tgt, remote_path)
        return error

    return None


def sftp_find(sftp, storagedir):
    """A very basic function to fetch a list of all available files on the remote SFTP share.
    This data is then used by a glue logic function in order to handle the actual selection,
    sftp_select_retrieval_target.

    :param sftp: a connection object as returned by sftp_connect
    :param storagedir: The remote root dir as passed through NS.
    :return:
    """

    try:
        if sftp.pwd != storagedir:
            sftp.chdir(storagedir)
            list_remote_files = sftp.listdir()
    except IOError:
        print("SFTP Root Directory Doesn't Exist: %s" % storagedir)
        list_remote_files = []

    # Paramiko and pysftp return unicode strings; we want to bash to local.
    list_returned = []
    for each in list_remote_files:
        if each.endswith(".tap") or each.endswith(".sig"):  # We are interested in only these extensions.
            list_returned.append(str(each))

    return list_returned


def sftp_place(connection, tgt, remote_path):
    error = None
    try:
        if str(connection.pwd) != remote_path:
            connection.chdir(remote_path)
        connection.put(tgt)
    except IOError as e:
        error = "Couldn't place file at %s; no such directory on remote host" % remote_path
        tgt = False
    except PermissionError:
        error = "Permission Denied"
        tgt = False

    return tgt, error


def sftp_retrieve_files(namespace, gpg_agent):
    ns = namespace
    gpg = gpg_agent  # Both for the sake of brevity
    print("Connecting to the remote SFTP store...")

    conn, error = sftp_connect(namespace)  # Get a connection and handle its errors if appropriate.
    if error is not None:
        print("An error has occurred in connecting.")
        print(error)
        print("Exiting...")
        ns.logs.log("An error occurred trying to connected to the SFTP Share: %s" % error)
        ns.logs.log("This was fatal to the operation of the program.")
        ns.logs.save()
        exit(5)

    list_all_files = sftp_find(conn, ns.dirNet)  # Get the full list of files stored remotely.
    list_target_files = sftp_select_retrieval_target(list_all_files)  # Get the files the user actually wants

    list_found_files = []

    is_error_notfound = False
    for file in list_target_files:  # physically retrieve those files.
        error = sftp_fetch(conn, ns.dirNet, file, ns.workDir)
        if error is not None:
            is_error_notfound = True
            print("%s - skipping" % error)
            ns.logs.log("%s - skipping" % error)
        else:
            list_found_files.append(os.path.join(ns.workDir, file))

    if is_error_notfound:
        print("One or more files were not able to be retrieved from the remote store.")
        print("If you wish do not wish to continue with only a partial restore, press ctrl+c now.")
        ns.logs.log("For the reasons above, this is a partial restore only.")
        foo = input("Press enter to continue.")

    # Now we need to obtain a recovery file of some kind.
    decrypted_first = tapestry.TaskDecrypt(os.path.join(ns.workDir, list_found_files[0]), ns.workDir, gpg_agent)
    decrypted_first = decrypted_first()
    debug_print("SRF: decrypted_first is: %s" % decrypted_first)
    debug_print("SRF: The conditional is therefore: %s" % decrypted_first.split(" ")[1].lower())
    if decrypted_first.split(" ")[1].lower() == "success":
        tar = tarfile.open(os.path.join(ns.workDir, decrypted_first.split(" ")[3].rstrip(".")), "r:*")
        # Hideous string management hack.
        tapfile_contents = tar.getnames()
        debug_print("The provided block contains: %s" % str(tapfile_contents))

        if "recovery-pkl" in tapfile_contents:
            index_file = tar.extractfile("recovery-pkl")
        elif "recovery-riff" in tapfile_contents:
            index_file = tar.extractfile("recovery-riff")
        else:
            index_file = open("/dev/null", "rb")  # Just for giggles
            print("Something has gone wrong!")
            print("One or more blocks are corrupt and missing their recovery index.")
            print("This is a fatal error.")
            ns.logs.log("One or more blocks are corrupt and missing their recovery indexes. This is a fatal error.")
            ns.logs.save()
            clean_up(ns.workDir)
            exit(5)
    else:
        print("Something has gone wrong in initial decryption.")
        print("Verify you have the key for the blocks provided and try again.")
        ns.logs.log("There was an error in the decryption of the recovery blocks. This is terminal.")
        ns.logs.save()
        clean_up(ns.workDir)
        exit(5)

    # If we made it this far, we have a recovery file, so let's return a recovery index
    rec_index = tapestry.RecoveryIndex(index_file)
    if len(list_found_files) != rec_index.blocks:
        print("There is a a mismatch in the number of recovered blocks and the amount of blocks listed in the"
              " recovery index. Would you like to continue?")
        input("Press enter to continue or ctrl+c to cancel.")

    ns.rec_index = rec_index

    return ns


def sftp_select_retrieval_target(list_available):
    """Accepts an sftp_find output list, and does some data processing before
    polling the user. Ultimately, returns a list of just the files for the
    relevant recovery record the user wishes to use.

    :param list_available:
    :return:
    """
    list_working = list_available.copy()  # We need a clone because we are going to break it up.
    # Then to kick out all the sigs (as duplicates)
    for file in list_working:
        if file.endswith(".sig"):
            list_working.remove(file)
    # Then we need a list of available machines
    dict_availability = {}
    for file in list_working:
        name_machine, year, month, day, blocknumber = file.split("-")
        date = ("%s-%s-%s" % (year, month, day))
        if name_machine not in dict_availability.keys():
            machine_entry = {"dates": {}}
            dict_availability.update({name_machine: machine_entry})
            # And a list of available dates (keyed by target machines)
        if date not in dict_availability[name_machine]["dates"].keys(): # And how many blocks are in each date.
            dict_availability[name_machine]["dates"].update({date: 1})
        else:
            new_count = dict_availability[name_machine]["dates"][date] + 1
            dict_availability[name_machine]["dates"].update({date: new_count})
    # Then, present the user with an arbitrary numbered list of machines to select from
    message = "The following machines are available from your SFTP share location. " \
              "Please enter the option number for the machine you'd like to recover locally."
    machine_selected = get_user_input(message, {"machine": dict_availability.keys()}, "machine")
    # Then the dates for the machines they selected
    dict_datecounts = dict_availability[machine_selected]["dates"]
    list_dates = []
    list_counts = []
    for date in dict_datecounts.keys():
        list_dates.append(date)
    list_dates.sort(reverse=True)  # Puts most recent first.
    for date in list_dates:  # Produces a list of block counts sorted by date, with dates presorted.
        list_counts.append(dict_datecounts[date])
    message = "For %s, you can choose from the following dates to recover from." % machine_selected
    date_selected = get_user_input(message, {"date": list_dates, "# of Blocks": list_counts}, "date")
    # finally, construct a list of both .tap and .sig files for the given machine and date.
    file_filter = "%s-%s" % (machine_selected, date_selected)
    list_to_fetch = []
    for file in list_available:
        if file.startswith(file_filter):
            list_to_fetch.append(file)

    return list_to_fetch


def prevalidate_blocks(namespace, list_blocks, index):
    if namespace.do_validation:
        ns = namespace
        ns.logs.log("Lines beneath this point are failed hash validation checks.")
        jobs = mp.JoinableQueue()
        for file in list_blocks:
            with tarfile.open(file, mode="r:*") as tf:
                list_members = tf.getnames()
                for member in list_members:
                    if member != "recovery-riff":  # Obviously we can't validate this noise.
                        task = tapestry.TaskCheckIntegrity(file, member, index[member]['sha256'])
                        jobs.put(task)
        workers = []
        sum_jobs = int(jobs.qsize())
        debug_print(sum_jobs)
        done = mp.JoinableQueue()
        for i in range(os.cpu_count()):
            workers.append(tapestry.ChildProcess(jobs, done, ns.workDir, ns.debug))
        rounds_complete = 0
        for w in workers:
            w.start()
        working = True
        status_print(rounds_complete, sum_jobs, "Checking Block Integrity", "Working...")
        # We removed the "... Working" message issue because this task returns useful messages.
        # This might get replaced when/if we include runtime logging again.
        while working:
            message = done.get()
            if message is None:
                working = False
            else:
                if message[0]:  # We only need to output the actual output if the job fails.
                    message[1] = "Working"
                else:
                    ns.logs.log(message[1])
            rounds_complete += 1
            if rounds_complete == sum_jobs:
                done.put(None)  # Use none as a poison pill to kill the queue.
            if rounds_complete <= sum_jobs:  # Patches the 200% bug.
                status_print(rounds_complete, sum_jobs, "Checking Block Integrity", message[1])
            done.task_done()
        jobs.join()
        for w in workers:  # Make extra certain all the children are dead.
            jobs.put(None)
        jobs.join()  # TODO replace lines below with better logic during the improved logging process.
        print("Please review the above lines for any failed files, and capture that information for your records.")
        print("Failures were also logged to %s" % ns.drop)
        ns.logs.log("Review lines above this mark for failed validation checks.")


def demand_validate(ns, gpg):
    """Provided the namespace and a gpg connection, take the argued path/list
    of paths pointing to a tapestry block and performs validation of the
    contents, then cleans itself up best as possible.

    :param ns: The entire tapestry namespace object.
    :param gpg: A valid GPG agent object.
    :return:
    """
    ns.logs.log("This run was a demand validation run; used to check only that block contents are valid.")
    if not os.path.exists(ns.workDir):
        os.mkdir(ns.workDir)
    path_arg = ns.validation_target
    if "," in path_arg:
        paths = path_arg.split(",")
    else:
        paths = [path_arg]

    for path in paths:
        if not os.path.isfile(path):  # We want to autoskip missing paths.
            paths.remove(path)
            print("Skipping: %s, file does not exist." % path)
            ns.logs.log("Skipping: %s, file does not exist." % path)
        if not path.endswith(".tap"):  # We can only work with our files!
            paths.remove(path)
            print("Skipping %s, not a tapestry block file!" % path)
            ns.logs.log("Skipping %s, not a tapestry block file!" % path)
    for path in paths:  # this list now consists of .tap files that actually exist!
        # Validate each block individually in case they don't belong to the same set.
        path_out = os.path.join(ns.workDir, os.path.basename(path))
        print("Attempting to validate %s" % os.path.basename(path))
        ns.logs.log("Attempting to validate %s" % os.path.basename(path))
        with open(path, "rb") as f:
            print("Decrypting the Block.")
            gpg.decrypt_file(f, always_trust=True, output=path_out)
        with tarfile.open(path_out, "r:*") as tf:
            if "recovery-riff" in tf.getnames():
                rec_file = tf.extractfile("recovery-riff")
                rec_index = tapestry.RecoveryIndex(rec_file)
                do_validate = True
            else:
                print("This file does not contain a RIFF-format recovery index and cannot be validated.")
                print("The file may be damaged, or have been created by a Pre-2.0 version of Tapestry.")
                ns.logs.log("This file does not contain a RIFF-format recovery index and cannot be validated.")
                ns.logs.log("The file may be damaged, or have been created by a Pre-2.0 version of Tapestry.")
                do_validate = False
        if do_validate:  # We step out at this level to close the tarfile in advance.
            prevalidate_blocks(ns, [path_out], rec_index)  # This allows multithreaded

    clean_up(ns.workDir)

