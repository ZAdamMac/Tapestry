#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules
import configparser as cp
import datetime as dt
import gnupg
import logging
import os
import shutil
import unittest

#  Stash classes and functions here if necessary.

#  Parse test config and build absolutized strings and things
cfg = cp.ConfigParser()
cfg.read("tapestry-test.cfg")



#  Establish a Logger for Test Output

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