"""Tapestry is a specialized backup tool for creating full-file backup packages
and storing them under conditions where the secrecy of the storage media is not
necessarily trusted. For complete usage information refer to the readme.md in
this package, or at the development repo:

github: https://www.github.com/ZAdamMac/Tapestry

"""

from ..Tapestry import classes
import argparse
import configparser
import os
import platform
import shutil

__version__ = "2.0.0"

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
        ns.fp = config.get("Environment Variables", "Expected FP")  # Can be changed during the finding process.
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
