"""
This script is a component of the Tapestry project's testing framework.
Specifically, this component defines helper classes and repeated functions for
all tests in the test script, in order to maximize reuse and provide a central
location for tidiness.

Author: Zac Adam-MacEwen (zadammac@kenshosec.com)
Tapestry is a product of Kensho Security Labs.
Produced under license.

Full license and documentation to be found at:
https://github.com/ZAdamMac/Tapestry
"""


from datetime import date
import os
import time

# Define the Classes We Use


class SimpleLogger:
    """A highly simplified logger used in tapestry's testing.
    """

    def __init__(self, landingdir, name, test):
        """Return a SimpleLogger object with the below properties

        :param landingdir: The path (ideally absolute) to the output file.
        :param name: The name of that logfile
        :param test: The name of the test being run.
        """

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

    def log(self, foo):
        """# Formats foo nicely and adds it to the log"""
        self.loggerfile.write(foo + '\n')

    def save(self):
        """saves the file to disk. Once used you have to re-instance the logger"""
        self.loggerfile.write("\n\n===============================[END OF TESTING]===============================")
        self.loggerfile.write("\n Tester Comments: ")
        self.loggerfile.write("\n This test was run on " + str(date.today()))
        self.loggerfile.flush()
        self.loggerfile.close()

# Define New Functions


def elapsed(start):
    """Quickly calculate the elapsed time between two points, to feed to the logger. Returns it formatted nicely.

    :param start: a time value, preferably grabbed from time.monotonic()
    :return:
    """
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
