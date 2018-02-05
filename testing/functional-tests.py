#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules
import configparser as cp
import date
import gnupg
import os
import shutil
import unittest

#  Stash classes and functions here if necessary.
class simpleLogger:  # dedicated skip-logging handler for use in buildBlocks
    def __init__(self, landingdir,name):  # starts the skiplogger and tells it it will be writing to landingdir with name
        landingAbs = os.path.join(landingdir, name)
        if not os.path.exists(landingdir):
            os.makedirs(landingdir)
        self.loggerfile = open(landingAbs, "w")  # This will REPLACE the existing logfile with the new one so be careful
        self.loggerfile.write("This is a log of tests run against some version of tapestry by the functional-tests.py testing utility. \n")
        self.loggerfile.write("\n")

    def log(self, foo):  # Formats foo nicely and adds it to the log
        self.loggerfile.write(foo + '\n')

    def save(self):  # saves the file to disk. Once used you have to re-instance the logger
        self.loggerfile.write("\n")
        self.loggerfile.write("\n This backup was run on " + str(date.today()))
        self.loggerfile.flush()
        self.loggerfile.close()

#  Parse test config
cfg = cp.ConfigParser()
cfg.read("tapestry-test.cfg")
out = cfg.get("Envrionment Variables", "output path")
uid = cfg.get("Environment Variables", "uid")
logs = os.path.join(out, "Logs")

#  Establish a Logger for Test Output
if not os.path.isdir((logs)):
    os.mkdir(logs)

logname = ("test-%s-%s.log" % (uid, str(date.today())))
log = simpleLogger(logs, logname)


#  Do the bulk runs and context switching to generate the test outputs (make sure to seperate outputs between runs!)

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