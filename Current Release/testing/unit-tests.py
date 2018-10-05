#! /usr/bin/python3.6
# Unit tests relating to Tapestry. Current as of 2.0.
# See the documentation - there are dependancies

# Import Block
from datetime import date
from testing import dev
from testing import framework as fw

# Extra Classes Go Here

# Define Tests As Functions Here
def testRIFFCompliance(namespace):
    pass

# Declare Some Constants

ns = type('',(),{})()  # We need a general-purpose namespace object
ns.keySig = 0 # TODO generate and encode
ns.keyCrypt = 0 # TODO GENERATE AND ENCODE
ns.goodRIFF = 0 # TODO Generate and Encode
ns.filename = "unit_test-"+str(ns.uid)+"-"+str(date.today())+".log"
ns.logger = fw.simpleLogger("Logs",ns.filename,"unit-tests")
