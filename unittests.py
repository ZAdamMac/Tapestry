#Unit Tests File for Tapestry
#To be run on all build versions before declaring release
#See, in-git, schemaTests.md for details

import datetime
import hashlib
import os
import time
import unittest

class testUnmodifiedCall(unittest.TestCase):
    def setUp(self):
        print("Begining testing against an unflagged call to the program.")
        with open("dev.py") as f:
            code = compile(f, "dev.py", "exec")
            timeStart = time.time()
            exec(code) # We generate output as though the program was called for a nonspecific run
            timeStop = time.time()
            diff = timeStop - timeStart
            print("Total runtime: %s seconds" %str(diff))

    def decryptable(self):  # Test to determine whether given .tap is decryptable
        pathUnderTest = ("/Tapestry_Testing/Results/Testbed-%s-1.tap" % datetime.date.today())
        tarUnderTest = "/Tapestry_Testing/Results/decrypted.tar.bz2"
        os.system("gpg --decrypt %s %s" % (pathUnderTest, tarUnderTest))
