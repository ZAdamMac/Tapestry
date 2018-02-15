#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules
import configparser as cp
from datetime import date
import gnupg
import mp5
import os
import shutil
import subprocess
import time
import unittest

#  Stash classes and functions here if necessary.
class simpleLogger:  # dedicated skip-logging handler for use in buildBlocks
    def __init__(self, landingdir,name):  # starts the skiplogger and tells it it will be writing to landingdir with name
        landingAbs = os.path.join(landingdir, name)
        if not os.path.exists(landingdir):
            os.makedirs(landingdir)
        self.loggerfile = open(landingAbs, "w")  # This will REPLACE the existing logfile with the new one so be careful
        self.loggerfile.write("This is a log of tests run against some version of tapestry by the functional-tests.py testing utility. \n")
        self.loggerfile.write("\n\n\n")
        self.loggerfile.write("===============")
        global host
        self.loggerfile.write("Test Host: %s \n" % host)
        cores = os.cpu_count()
        self.loggerfile.write("Cores Available: %s \n" % cores)
        RAM = os.popen("free -m").readlines()[1].split()[1]
        self.loggerfile.write("RAM Available: %s MB \n" % RAM)
        self.loggerfile.write("===============")

    def log(self, foo):  # Formats foo nicely and adds it to the log
        self.loggerfile.write(foo + '\n')

    def save(self):  # saves the file to disk. Once used you have to re-instance the logger
        self.loggerfile.write("\n")
        self.loggerfile.write("\n This test was run on " + str(date.today()))
        self.loggerfile.flush()
        self.loggerfile.close()

def elapsed(start):  #Quickly calculate the elapsed time between two points, to feed to the logger. Returns it formatted nicely.
    current = time.monotonic()
    secElapsed = current - start
    strElapsed = time.strftime("%H:%M:%S", time.gmtime(secElapsed))

#  Parse test config
os.chdir(os.getcwd())

cfg = cp.ConfigParser()
cfg.read("tapestry-test.cfg")
out = cfg.get("Environment Variables", "output path")
uid = cfg.get("Environment Variables", "uid")
host = cfg.get("Environment Variables", "compID")
logs = os.path.join(out, "Logs")

shutil.copy("tapestry-test.cfg", "tapestry-test.cfg.bak") # We create a backup of the config to restore to after testing.

cfg.set("Environment Variables", "output path", os.path.join(out, "Non-Inc"))
with open("tapestry-test.cfg", "w") as warp:
    cfg.write(warp)

#  Establish a Logger for Test Output
if not os.path.isdir((logs)):
    os.mkdir(logs)

logname = ("test-%s-%s.log" % (uid, str(date.today())))
log = simpleLogger(logs, logname)


#  Do the bulk runs and context switching to generate the test outputs (make sure to seperate outputs between runs!)
if not os.path.isdir(os.path.join(out, "Non-Inc")):
    os.mkdir(os.path.join(out, "Non-Inc"))
waiting = subprocess.run(("python3.6", "dev.py", "--genKey"))

cfg.set("Environment Variables", "output path", os.path.join(out, "Inc"))
with open("tapestry-test.cfg", "w") as warp:
    cfg.write(warp)

waiting = subprocess.run(("python3.6", "dev.py", "--inc"))

cfg.set("Environment Variables", "output path", os.path.join(out,"Corpus"))
docs = cfg.get("Default Locations/Nix", "docs")
cfg.set("Default Locations/Nix", "docs", docs.replace("Control", "Test"))
pics = cfg.get("Default Locations/Nix", "photos")
cfg.set("Default Locations/Nix", "photos", pics.replace("Control", "Test"))
vids = cfg.get("Additional Locations/Nix", "video")
cfg.set("Default Locations/Nix", "video", vids.replace("Control", "Test"))
cfg.remove_option("Additional Locations/Nix", "Music") # This should still wind up in corpus if you didn't break directionless recovery.
with open("tapestry-test.cfg", "w") as warp:
    cfg.write(warp)

waiting = subprocess.run(("python3.6", "dev.py", "--rcv"))

shutil.copy("tapestry-test.cfg.bak", "tapestry-test.cfg")

#  Identity Testing
    #  Hash to Hash of Corpuses

#  Encryption and Signing Passing
    # Test if Signatures are Valid
    # If Identity failed, test encryption

#  Version Specificity
    # If Identity failed, compare a test pickle to control pickle.
    # Report the diff (pass if no diff)

#  Compression Testing
    # Test that output is smaller than Blocksize

#  Export Check
    # Check for output!

#  Clear Down!