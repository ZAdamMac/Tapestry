"""Tapestry is a specialized backup tool for creating full-file backup packages
and storing them under conditions where the secrecy of the storage media is not
necessarily trusted. For complete usage information refer to the readme.md in
this package, or at the development repo:

github: https://www.github.com/ZAdamMac/Tapestry

"""

from ..Tapestry import classes as tapestry
import argparse
import configparser
import ftplib
import getpass
import gnupg
import multiprocessing as mp
import os
import platform
import shutil
import ssl
import sys
import tarfile

__version__ = "2.0.0"

# Class Definitions


class Namespace(object):  # this just creates an object with arbitrary attributes.
    pass

# Function Definitions


def announce():
    """Simple code for printing out the greeting on startup."""
    if __name__ == '__main__':
        print("Welcome to Tapestry Backup Tool Version " + __version__)
        print("Automatic updates are not currently a function of this script.")
        print("Please refer to the repo for updates: https://www.github.com/ZAdamMac/Tapestry")
        debug_print("The current OS is: " + platform.system())


def clean_up(working_directory):
    """Releases the memory space used up by temp, because we're polite."""
    if __name__ == "__main__":
        if os.path.exists(working_directory):
            shutil.rmtree(working_directory)


def debug_print(body):
    """Checks for the value of a global variable, debug, and determines whether
    or not to print the "body" argument to stout.
    """
    output_string = str(body)
    global state
    if state.debug:
        print(output_string)


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
    if __name__ == "__main__":
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
        while working:
            message = done.get()
            if message is None:
                working = False
            else:
                rounds_complete += 1
                status_print(rounds_complete, sum_jobs, "Decrypting")
                debug_print(message)
                if rounds_complete == sum_jobs:
                    done.put(None)  # Use none as a poison pill to kill the queue.
                done.task_done()
        tasks.join()
        for w in workers:
            tasks.put(None)


def do_main(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire build process."""
    pass


def do_recovery(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire recovery process."""
    ns = namespace
    if namespace.modeNetwork.lower() == "ftp":
        namespace = ftp_retrieve_files(namespace, gpg_agent)
    else:
        rec_index = media_retrieve_files(namespace.workDir, namespace.workDir,
                                         gpg_agent)
        namespace.rec_index = rec_index
    verified_blocks = verify_blocks(ns.workDir, gpg_agent)
    decrypt_blocks(ns, verified_blocks, gpg_agent)
    unpack_blocks(ns)
    clean_up(ns.workDir)
    exit()


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
    fp = keypair.fingerprint  # Changes the value of FP to the new key

    config = configparser.ConfigParser()
    if namespace.devtest:
        cfg = "tapestry-test.cfg"
    else:
        cfg = "tapestry.cfg"

    if os.path.exists(os.getcwd() + "/" + cfg):
        config.read(cfg)
    config.set("Environment Variables", "Expected FP", str(fp))  # sets this value in config
    namespace.activeFP = keypair.fingerprint
    with open(cfg, "w") as cf:
        config.write(cf)

    if not os.path.isdir(namespace.drop):
        os.mkdir(namespace.drop)
    os.chdir(namespace.drop)
    pub_out = gpg_agent.export_keys(fp)
    pub_file = os.open("DRPub.key", os.O_CREAT | os.O_RDWR)
    pub_handle = os.fdopen(pub_file, "w")
    pub_handle.write(str(pub_out))
    pub_handle.close()
    try:
        key_out = gpg_agent.export_keys(fp, True, expect_passphrase=False)
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

    found_blocks = []
    found_sigs = []
    initial_block_hunt = True

    while initial_block_hunt:
        for location, sub_directories, files in os.walk(mountpoint):
            for file in files:
                if file.endswith(".tap"):
                    found_blocks.append(file)
                    shutil.copy(file, os.path.join(temp_path, file))
                elif file.endswith(".tap.sig"):
                    found_sigs.append(file)
                    shutil.copy(file, os.path.join(temp_path, file))

        if len(found_blocks) == 0:
            print("The are no recovery files on the mountpoint at %s" % mountpoint)
            print("Check the media is inserted correctly (or that that address is correct) and try again.")
            input("Press enter to continue")
        else:
            initial_block_hunt = False

    # Now we need to obtain a recovery file of some kind.
    decrypted_first = tapestry.TaskDecrypt(found_blocks[0], temp_path, gpg_agent)
    decrypted_first = decrypted_first()
    if decrypted_first.split()[1].lower == "success":
        tar = tarfile.open(os.path.join(temp_path, found_blocks[0]), "r:*")
        tapfile_contents = tar.getnames()

        if "recovery-pkl" in tapfile_contents:
            index_file = tar.extractfile("recovery-pkl")
        elif "recovery-riff" in tapfile_contents:
            index_file = tar.extractfile("recovery-riff")
        else:
            index_file = open("/dev/null", "rb") # Just for giggles
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


def parse_args(namespace):
    """Parse arguments and return the modified namespace object"""
    if __name__ == "__main__":
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
        args = parser.parse_args()

        ns.rcv = args.rcv
        ns.inc = args.inc
        ns.debug = args.debug
        ns.devtest = args.devtest
        ns.genKey = args.genKey

        return ns


def parse_config(namespace):
    """mounts the configparser instance, grabs the config file, and passes its
    values into the namespace.
    """
    ns = namespace
    if __name__ == "__main__":
        config = configparser.ConfigParser()
        if ns.devtest:
            cfg = "tapestry-test.cfg"
        else:
            cfg = "tapestry.cfg"

        if os.path.exists(os.getcwd() + "/" + cfg):
            config.read(cfg)
        else:
            print("The Appropriate config file: %s cannot be found." % cfg)
            exit()

        ns.expectedFP = config.get("Environment Variables", "Expected FP")
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
        ns.nameNet = config.get("Network Configuration", "remote drop location")
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
            ns.workDir = "C:/Windows/Temp"
            ns.desktop = str("C:/Users/" + ns.uid + "/Desktop")
            ns.gpgDir = "C:/Program Files (x86)/GNU/GnuPG"
        ns.numConsumers = os.cpu_count()
        debug_print("I am operating with %s consumers." % ns.numConsumers)

        # lastly, now that we know current OS, let's build the dictionary of categories
        ns.category_paths = {}
        if ns.currentOS == "Linux":
            relevant = "Default Locations/Nix"
        else:
            relevant = "Default Locations/Windows"
        for categories in config.options(relevant):
            for category in categories:
                category_path = config.get(relevant, category)
                ns.category_paths.update({category: category_path})
        if ns.currentOS == "Linux":
            relevant = "Additional Locations/Nix"
        else:
            relevant = "Additional Locations/Windows"
        for categories in config.options(relevant):
            for category in categories:
                category_path = config.get(relevant, category)
                ns.category_paths.update({category: category_path})


    return ns


def start_gpg(ns):
    """Starts the GPG handler based on the current state. If --devtest or
    --debug were passed at runtime, the gpg handler will be verbose.
    """
    verbose = False
    if ns.debug or ns.devtest:
        verbose = True
    gpg = gnupg.GPG(gnupghome=ns.gpgDir, verbose=verbose)

    return gpg


def status_print(done, total, job):
    """Prints a basic status message. If not interrupted, prints it on one line"""
    lengthBar = 15.0
    doneBar = int(round((done / total) * lengthBar))
    doneBarPrint = str("#" * int(doneBar) + "-" * int(round((lengthBar - doneBar))))
    percent = int(round((done / total) * 100))
    text = ("\r{0}: [{1}] {2}%".format(job, doneBarPrint, percent))
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
                files_to_unpack.update({file, block})

    tasks = mp.JoinableQueue()  # Let's populate the queue
    for file, block in files_to_unpack:
        skip = False
        category_label, sub_path = ns.rec_index.find(file)
        if category_label == b"404":
            skip = True
        elif category_label == "skip":
            skip = True
        try:
            category_dir = ns.category_paths[category_label]
        except KeyError:
            category_dir = ns.drop
        if not skip:
            tap_absolute = os.path.join(ns.workDir, block)
            tasks.put(tapestry.TaskTarUnpack(tap_absolute, file, category_dir, sub_path))
    sum_jobs = tasks.qsize()

    workers = []
    done = mp.JoinableQueue
    for i in range(os.cpu_count()):
        workers.append(tapestry.ChildProcess(tasks, done, ns.workDir, ns.debug))
    rounds_complete = 0
    for w in workers:
        w.start()
    working = True
    while working:
        message = done.get()
        if message is None:
            working = False
        else:
            rounds_complete += 1
            status_print(rounds_complete, sum_jobs, "Unpacking")
            debug_print(message)
            if rounds_complete == sum_jobs:
                done.put(None)  # Use none as a poison pill to kill the queue.
            done.task_done()
    tasks.join()
    for w in workers:
        tasks.put(None)


def verify_blocks(namespace, gpg_agent):
    """Verifies blocks and returns a list of verified blocks as a result"""
    ns = namespace
    gpg = gpg_agent
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
                resume = input("Approve this fingerprint? (y/n)")
                if "y" in resume.lower():
                    valid_blocks.append(block)
                    approved_fingerprints.append(fingerprint)
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


#  Runtime Follows
if __name__ == "__main__":
    announce()
    state = Namespace()
    state = parse_args(state)
    state = parse_config(state)
    gpg_conn = start_gpg(state)
    if state.genKey:
        state = generate_keys(state, gpg_conn)
    verify_keys(state, gpg_conn)
    if state.rcv:
        do_recovery(state, gpg_conn)
    else:
        do_main(state, gpg_conn)
    clean_up(state.workDir)
    exit()
