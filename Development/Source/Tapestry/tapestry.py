"""Tapestry is a specialized backup tool for creating full-file backup packages
and storing them under conditions where the secrecy of the storage media is not
necessarily trusted. For complete usage information refer to the readme.md in
this package, or at the development repo:

github: https://www.github.com/ZAdamMac/Tapestry

"""

from ..Tapestry import classes
import argparse
import configparser
import gnupg
import os
import platform
import shutil

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


def do_main(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire build process."""
    pass


def do_recovery(namespace, gpg_agent):
    """Basic function that holds the runtime for the entire recovery process."""
    pass


def generate_keys(namespace, gpg_agent):
    """Provided with a namespace and a connection to the gpg agent, generates a
    new key. Does not obviate the build runtime.
    """
    print("You have indicated you wish to have Tapestry generate a new Disaster Recovery Key.")
    print(("This key will be a %s -bit RSA Key Pair with the credentials you specify." % namespace.keysize))
    print("This key will not expire by default. If you need this functionality, add it in GPG.")
    nameKey = str(input("User/Organization Name: "))
    contactKey = str(input("Recovery Contact Email: "))
    print("You will be prompted externally to enter a passphrase for this key via your default pinentry program.")
    inp = gpg_agent.gen_key_input(key_type="RSA", key_length=namespace.keysize,
                                  name_real=nameKey, name_comment="Tapestry Recovery",
                                  name_email=contactKey)
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
    pubOut = gpg_agent.export_keys(fp)
    pubFile = os.open("DRPub.key", os.O_CREAT | os.O_RDWR)
    pubHandle = os.fdopen(pubFile, "w")
    pubHandle.write(str(pubOut))
    pubHandle.close()
    try:
        keyOut = gpg_agent.export_keys(fp, True, expect_passphrase=False)
        keyFile = os.open("DR.key", os.O_CREAT | os.O_RDWR)
        keyHandle = os.fdopen(keyFile, "w")
        keyHandle.write(str(keyOut))
        keyHandle.close()
    except ValueError: # Most Probable cause for this is that the version of the gnupg module is outdated
        print("An error has occured which prevented the private side of the disaster recovery key from being exported.")
        print("This error is likely caused by this system's version of the python-gnupg module being outdated.")
        print("You can export the key manually using the method of your choice.")

    print("The new keys have been saved in the output folder. Please move them to removable media or other backup.")

    return namespace

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
            2 ** 20)  # The math is ncessary to go from MB to Bytes)
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

    return ns


def start_gpg(state):
    """Starts the GPG handler based on the current state. If --devtest or
    --debug were passed at runtime, the gpg handler will be verbose.
    """
    verbose = False
    if state.debug or state.devtest:
        verbose = True
    gpg = gnupg.GPG(gnupghome=state.gpgDir, verbose=verbose)

    return gpg

def verify_keys(ns, gpg):
    """Verify that the keys intended for use are present."""
    keys = gpg.list_keys(keys=ns.fp)
    try:
        location = keys.key_map[ns.fp]  # If the key is in the dictionary, hooray!
        found = True
    except KeyError:
        found = False
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
        state = generate_keys(state)
    verify_keys(state)
    if state.rcv:
        do_recovery(state, gpg_conn)
    else:
        do_main(state, gpg_conn)
    clean_up(state.workDir)
    exit()
