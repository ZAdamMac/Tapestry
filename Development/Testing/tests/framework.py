#! /usr/bin/Python3.6
# Basics Module for the Tapestry Testing framework. Should be stored in same
# dir as the test framework itself as the other tests.old all import from this.

# Imports block - it's dependencies all the way down!
from datetime import date
import os
import time

# Define the Classes We Use
class SimpleLogger:  # dedicated skip-logging handler for use in buildBlocks
    def __init__(self, landingdir,name, test):  # starts the skiplogger and tells it it will be writing to landingdir with name
        landingAbs = os.path.join(landingdir, name)
        if not os.path.exists(landingdir):
            os.makedirs(landingdir)
        self.loggerfile = open(landingAbs, "w")  # This will REPLACE the existing logfile with the new one so be careful
        self.loggerfile.write("===============================================================================\nThis is a log of tests run against some version of Tapestry by the \n%s.py testing utility. The date is indicated in the filename. \nIt should be made clear that these tests do not indicate any sort of warranty \nor guarantee of merchantability.\n\n=======TEST MACHINE SPECS=======\n" % str(test))
        cores = os.cpu_count()
        self.loggerfile.write("Cores Available: %s \n" % cores)
        RAM = os.popen("free -m").readlines()[1].split()[1]
        self.loggerfile.write("RAM Available: %s MB \n" % RAM)
        self.loggerfile.write("================================\n\n\n\n================================BEGIN TESTING==================================\n")

    def log(self, foo):  # Formats foo nicely and adds it to the log
        self.loggerfile.write(foo + '\n')

    def save(self):  # saves the file to disk. Once used you have to re-instance the logger
        self.loggerfile.write("\n\n===============================[END OF TESTING]===============================")
        self.loggerfile.write("\n Tester Comments: ")
        self.loggerfile.write("\n This test was run on " + str(date.today()))
        self.loggerfile.flush()
        self.loggerfile.close()

# Define New Functions
def elapsed(start):  #Quickly calculate the elapsed time between two points, to feed to the logger. Returns it formatted nicely.
    current = time.monotonic()
    secElapsed = current - start
    strElapsed = time.strftime("%H:%M:%S", time.gmtime(secElapsed))
    return strElapsed


def validate_dict_config(config, expected):
    """Validate that everything needed in these tests is present in the config
    dictionary provided by main. This should be updated if any new parameters
    are needed. Each test suite needs to test for its own set of valid values.

    :param config: dictionary argued in.
    :param expected: a list of expected keys for the config dictionary.
    :return: Boolean of True if valid.
    """
    failed = False
    for key in expected:
        try:
            valid = config[key]
        except KeyError:
            failed = True

    return not failed
