#Unit Tests File for Tapestry
#To be run on all build versions before declaring release
#See, in-git, schemaTests.md for details

import unittest
import dev as tapestry
import os

class testUnmodifiedCall(unittest.TestCase):
    def setUp(self):
        pass