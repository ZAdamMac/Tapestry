"""Use me to run all the tests in the suite.

This version is current as of Tapestry 2.0's development cycle. Simply invoke,
the script will call all the relevant runtimes. As long as the tests themselves
aren't buggy and Tapestry isn't raising any unhandled exceptions, the testing
results will appear in the logs.
"""

from ..Testing import integrity_tests, network_tests, runtime_tests, unit_tests

print("Okay, starting the tests.")
print("Starting the Runtime Test.")
runtime_tests.runtime()
print("Starting the Integrity Tests.")
integrity_tests.runtime()
print("Starting the Unit Tests")
unit_tests.runtime()
print("Starting the Network Tests.")
network_tests.runtime()
print("All tests complete.")
exit()
