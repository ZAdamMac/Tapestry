"""Tapestry is a specialized backup tool for creating full-file backup packages
and storing them under conditions where the secrecy of the storage media is not
necessarily trusted. For complete usage information refer to the readme.md in
this package, or at the development repo:

github: https://www.github.com/ZAdamMac/Tapestry

"""

from . import classes as tapestry
import argparse
import configparser
import datetime
import ftplib
import getpass
import gnupg
import hashlib
import io
import multiprocessing as mp
import os
import platform
from random import shuffle
import shutil
import ssl
import sys
import tarfile
import uuid

__version__ = "2.0.2"

# Class Definitions


class Namespace(object):  # this just creates an object with arbitrary attributes.
    pass

# Function Definitions


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
                size = os.path.getsize(absolute_path)
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
                    print("{%s} %s is larger than %s (%s) and is being excluded" %
                          (category, file, size_pretty, block_size_pretty))

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
    prevalidate_blocks(ns, list_blocks, raw_recovery_index)
    encrypt_blocks(list_blocks, gpg_agent, ns.activeFP, ns)
    sign_blocks(namespace, gpg_agent)
    if namespace.modeNetwork.lower() == "ftp":
        ftp_deposit_files(namespace)
    clean_up(namespace.workDir)
    print("The temporary working directories have been cleared and your files")
    print("are now stored here: %s" % namespace.drop)
    exit()


def do_recovery(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire recovery process."""
    ns = namespace
    print("Entering Recovery Mode")
    if ns.modeNetwork.lower() == "ftp":
        print("Fetching available blocks from the FTP server.")
        namespace = ftp_retrieve_files(namespace, gpg_agent)
        print("FTP Fetch Completed")
    else:
        rec_index = media_retrieve_files(namespace.recovery_path, namespace.workDir,
                                         gpg_agent)
        namespace.rec_index = rec_index
        debug_print("DoRecovery: namespace after MRF: %s" % namespace)
    verified_blocks = verify_blocks(namespace, gpg_agent)
    decrypt_blocks(namespace, verified_blocks, gpg_agent)
    decompress_blocks(namespace)
    unpack_blocks(namespace)
    clean_up(namespace.workDir)
    debug_print("REC: Got this far, so I should terminate")
    exit()


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


def ftp_deposit_files(ns):
    """Based on the usual network config, sends any local blocks in ns.drop."""
    if ns.modeNetwork.lower() == "ftp":
        input("""Tapestry is presently configured to use an FTP drop. 
        Please ensure you have a connection, and press any key to continue.""")
        pw = getpass.getpass("Enter the FTP password now (if required):")
        ftp_link = ftp_establish_connection(ns.addrNet, ns.portNet, get_ssl_context(ns), ns.nameNet, pw)
        list_outbound_files = []
        for location, sub_dirs, files in os.walk(ns.drop):
            for file in files:
                if file.endswith(".tap") or file.endswith(".sig"):
                    list_outbound_files.append(os.path.join(location, file))
        print("The following files will be uploaded to the FTP:")
        for file in list_outbound_files:
            print(os.path.basename(file))
        print("Now beggining the upload. You will be notified when this process is completed.")
        for file in list_outbound_files:
            ftp_send_block(file, ftp_link, ns.dirNet)
        if ns.retainLocal:
            print("The upload process is now completed.")
            print("You have selected to store local copies of these files.")
            print("Those files can be found here %s" % ns.drop)
        else:
            print("You have not configured to retain local copies, so we will delete those for you.")
            for file in list_outbound_files:
                os.remove(file)
            print("The files which were archived to the FTP have been removed.")
            print("Other output files, such as logs or the RIFF, are not removed.")


def ftp_establish_connection(url, port, ssl_context, username, password):
    """Establish and return a valid ftp(/tls) object."""
    if username is not None:
        if password is None:
            password = ""
    elif username is None:
        username = ''
    if port is None:
        port = 21
    if ssl_context is None:
        link = ftplib.FTP()
    else:
        link = tapestry.FTP_TLS(context=ssl_context)
        link.connect(host=url, port=port)
        try:
            link.auth()
        except ssl.SSLError:
            raise ConnectionRefusedError
        link.prot_p()
    if username != '':
        link.login(user=username, passwd=password)
    return link


def ftp_fetch_block(fname, ftp_connect, dir_destination):
    """fetch fname from the server"""
    if dir_destination != "":
        if not os.path.exists(dir_destination):
            os.mkdir(dir_destination)
    with open(os.path.join(dir_destination, fname), "wb") as fo:
        ftp_connect.retrbinary(("RETR %s" % fname), fo.write)


def ftp_grep_blocks(label, date, ftp_connect):
    """fetch the list of blocks from Label on Date."""
    index = ftp_connect.nlst()
    lead = ("%s-%s" % (label, date))
    list_fetch = []
    for file in index:
        if file.startswith(lead):
            list_fetch.append(file)
    return len(list_fetch), list_fetch


def ftp_retrieve_files(ns, gpg):
    """Based on the usual network config, retrieves the current blocks."""
    if ns.modeNetwork.lower() == "ftp":
        input("""Tapestry is presently configured to use an FTP drop. 
        Please ensure you have a connection, and press any key to continue.""")
        use_default_comp_id = input("Would you like to recover files for %s? (y/n)>" % ns.compid).lower()
        if use_default_comp_id == "n":
            print("Please enter the name of the computer you wish to recover files for:")
            compid = input("Case Sensitive: ")
        else:
            compid = ns.compid
        print("Please enter the date for which you wish to recover files:")
        tgt_date = input("YYYY-MM-DD")
        pw = getpass.getpass("Enter the FTP password now (if required):")
        ftp_link = ftp_establish_connection(ns.addrNet, ns.portNet, get_ssl_context(ns), ns.nameNet, pw)
        count_blocks, list_blocks = ftp_grep_blocks(compid, tgt_date, ftp_link)
        if count_blocks == 0:
            print("No blocks for that date were found - check your records and try again.")
            ftp_link.quit()
            exit()
        else:
            ns.media = ns.workDir
            for block in list_blocks:
                ftp_fetch_block(block, ftp_link, ns.media)
            ftp_link.quit()

        decrypted_first = tapestry.TaskDecrypt(list_blocks[0], ns.workDir, gpg)
        decrypted_first = decrypted_first()
        if decrypted_first.split()[1].lower == "success":
            tar = tarfile.open(os.path.join(ns.workDir, list_blocks[0]), "r:*")
            tapfile_contents = tar.getnames()

            if "recovery-pkl" in tapfile_contents:
                index_file = tar.extractfile("recovery-pkl")
            elif "recovery-riff" in tapfile_contents:
                index_file = tar.extractfile("recovery-pkl")
            else:
                print("Something has gone wrong!")
                print("One or more blocks are corrupt and missing their recovery index.")
                print("This is a fatal error.")
                exit()
        else:
            print("Something has gone wrong in initial decryption.")
            print("Verify you have the key for the blocks provided and try again.")
            exit()
        ns.rec_index = tapestry.RecoveryIndex(index_file)
        return ns


def ftp_send_block(fname, ftp_connect, dir_destination):
    """Send target to the server"""
    list_remote_directories = ftp_connect.dir()
    if list_remote_directories is not None:
        if dir_destination not in list_remote_directories:
            try:
                ftp_connect.mkd(dir_destination)
            except ftplib.all_errors:
                print("Something went wrong while creating the target directory on the FTP.")
                print("The archives are being retained locally. Please upload manually.")
                print("Check your tapestry and FTP configuration.")
                exit()
    command = "STOR %s" % fname
    with open(fname, "rb") as fd:
        ftp_connect.storbinary(command, fd)


def get_ssl_context(ns, test=False):
    """Construct and return an appropriately-configured SSL Context object."""
    tls_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    tls_context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
    if ns.modeNetwork.lower() == "loom":
        tls_context.load_cert_chain(ns.clientCert)
    if test:
        tls_context.load_verify_locations(cafile="testcert.pem")
    return tls_context


def generate_keys(namespace, gpg_agent):
    """Provided with a namespace and a connection to the gpg agent, generates a
    new key. Does not obviate the build runtime.
    """
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
    except ValueError:  # Most Probable cause for this is that the version of the gnupg module is outdated
        print("An error has occured which prevented the private side of the disaster recovery key from being exported.")
        print("This error is likely caused by this system's version of the python-gnupg module being outdated.")
        print("You can export the key manually using the method of your choice.")

    print("The new keys have been saved in the output folder. Please move them to removable media or other backup.")

    return namespace


def media_retrieve_files(mountpoint, temp_path, gpg_agent):
    """Iterates over mountpoint, moving .tap files and their signatures to the
    temporary working directory. Early in operation, will retrieve the recovery
    pickle or NewRIFF index from the first block it finds.

    :param mountpoint: absolute path to the media mountpoint.
    :param temp_path: absolute path to the system's working directory.
    :param gpg_agent: a python-gnupg gpg agent object
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
            exit()
    else:
        print("Something has gone wrong in initial decryption.")
        print("Verify you have the key for the blocks provided and try again.")
        exit()

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
        for item in sizes:
            placed = working_block.put(item, ops_list[item])
            if placed:
                sizes.remove(item)
        if working_block.full:  # We need a new block, unpacked items.
            collection_blocks.append(working_block)
            counter += 1
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
                               str(datetime.date.today()), None, ops_list, ns.drop)
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
    args = parser.parse_args()

    ns.rcv = args.rcv
    ns.inc = args.inc
    ns.debug = args.debug
    ns.devtest = args.devtest
    ns.genKey = args.genKey
    ns.config_path = args.c

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
        for item in sizes:
            placed = working_block.put(item, ops_list[item])
            if placed:
                sizes.remove(item)
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
                               str(datetime.date.today()), None, ops_list, ns.drop)
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
        exit()

    ns.activeFP = config.get("Environment Variables", "Expected FP")
    ns.fp = config.get("Environment Variables", "Expected FP")
    ns.signing = config.getboolean("Environment Variables", "Sign by Default")
    ns.sigFP = config.get("Environment Variables", "Signing FP")
    ns.keysize = config.getint("Environment Variables", "keysize")
    ns.compress = config.getboolean("Environment Variables", "Use Compression")
    ns.compressLevel = config.getint("Environment Variables", "Compression Level")
    ns.step = "none"
    ns.sumJobs = 0
    ns.jobsDone = 0
    ns.modeNetwork = config.get("Network Configuration", "mode")
    ns.addrNet = config.get("Network Configuration", "server")
    ns.portNet = config.getint("Network Configuration", "port")
    ns.nameNet = config.get("Network Configuration", "username")
    ns.dirNet = config.get("Network Configuration", "remote drop location")
    ns.retainLocal = config.getboolean("Network Configuration", "Keep Local Copies")
    ns.block_size_raw = config.getint("Environment Variables", "blockSize") * (
        2 ** 20)  # The math is necessary to go from MB to Bytes)
    ns.compid = config.get("Environment Variables", "compid")
    ns.recovery_path = config.get("Environment Variables", "recovery path")
    ns.uid = config.get("Environment Variables", "uid")
    ns.drop = config.get("Environment Variables", "Output Path")

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

    dict_default_config = {
        "Environment Variables": {
            "uid": "your_uid",
            "compid": "your_hostname",
            "blocksize": 4096,
            "expected FP": "Provide Encryption Key Fingerprint or run with option --genKey",
            "sign by default": True,
            "signing FP": "Provide signing key fingerprint",
            "recovery path": "Provide path to the recovery file location, ex. /media/ or D:/",
            "output path": "Provide path to the output for recovery file and logs.",
            "keysize": 2048,
            "use compression": True,
            "compression level": 2
        },
        "Network Configuration": {
            "mode": "none",
            "server": "localhost",
            "port": 21,
            "username": "ftptest",
            "remote drop location": "path on the ftp to which to drop files",
            "keep local copies": True
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
        exit()
    debug_print("Fetching key %s from Keyring" % ns.activeFP)
    debug_print(ns.activeFP)


def runtime():
    global state
    state = Namespace()
    state = parse_args(state)
    state = parse_config(state)
    gpg_conn = start_gpg(state)
    announce()
    if state.demand_validate:
        demand_validate(state, gpg_conn)  # TODO ensure defined
    if state.genKey:
        state = generate_keys(state, gpg_conn)
    verify_keys(state, gpg_conn)
    if state.rcv:
        do_recovery(state, gpg_conn)
    else:
        do_main(state, gpg_conn)
    clean_up(state.workDir)
    exit()


def prevalidate_blocks(namespace, list_blocks, index):
    if namespace.do_validation:  # TODO add to configparse and argparse
        ns = namespace
        jobs = mp.JoinableQueue()
        for file in list_blocks:
            with tarfile.open(file, mode="r:") as tf:
                list_members = tf.getnames()
                for member in list_members:
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
            if message[0]:  # We only need to output the actual output if the job fails.
                message[1] = "Working"
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
        foo = input("Press Enter to Continue")  # Pausing for input here is not long-term acceptable; breaks automation


def recovery_validate_files(namespace):
    """Provided a namespace object, this function will crawl the defined
    working directory, looking for decrypted and decompressed tap files to
    validate the contents of.

    :param namespace: The system namespace object.
    :return:
    """
    ns = namespace

    found_decrypted = []  # Need to find all the decrypted blocks
    for foo, bar, files in os.walk(ns.workDir):
        for file in files:
            if file.endswith(".decrypted"):
                found_decrypted.append(os.path.join(foo, file))

    prevalidate_blocks(ns, found_decrypted, ns.rec_index["index"])
