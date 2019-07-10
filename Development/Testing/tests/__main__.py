"""
This script is a component of the testing framework for the Tapestry
back-up tool.

The intended purpose of the script is to be run prior to commit, with
the appropriate flags set, for pre-commit code validation.

Author: Zac Adam-MacEwen (zadammac@kenshosec.com)
Tapestry is a product of Kensho Security Labs.
Produced under license.

Full license and documentation to be found at:
https://github.com/ZAdamMac/Tapestry
"""

from . import positive_tests, runtime_tests, negative_tests
import argparse
import configparser
import os

__version__ = "2.1.0dev"


def parse_config():
    """Does traditional config parsing to return a dictionary of config values.

    :return : Returns "dict_config", a dictionary of config key-value pairs.
    """
    parser = configparser.ConfigParser()
    os.chdir(os.path.dirname(__file__))
    if os.path.isfile("test_config.cfg"):
        parser.read("test_config.cfg")
    else:
        print("The expected test_config.cfg file is missing from %s" % os.path.dirname(__file__))
        print("Please ensure the test file is available to this script and run again.")
        exit(0)

    test_user = parser.get("Tester Information", "username")
    path_logs = parser.get("Environment Information", "Logs Path")
    path_config = parser.get("Environment Information", "Logs Path")
    path_corpus = parser.get("Environment Information", "Corpus Path")
    path_temp = parser.get("Environment Information", "Runtime Output Path")

    configuration = {"test_user": test_user, "path_logs": path_logs,
                     "path_config": path_config, "path_corpus": path_corpus,
                     }

    return configuration


def parse_args():
    """Sets up the argument parser, but also provides all the relevant argparser
    configuration for the CLI.

    :return: dict_args
    """
    parser = argparse.ArgumentParser(description="""
            Run through the automated testing for Tapestry development builds. 
            \n Full documentation at https://github.com/ZAdamMac/Tapestry/blob/master/TESTDOCS.md
                                            """)
    parser.add_argument('--net', help="Skip network unit tests.",
                        action="store_true")
    parser.add_argument('--runtime', help="Include the full-runtime integration tests",
                        action="store_true")
    args = parser.parse_args()

    arguments = {}
    arguments.update({"do_network_tests": args.net})
    arguments.update({"runtime": args.runtime})

    return arguments

if __name__ == "__main__":
    print("Tapestry Test Automation - Version %s" % __version__)
    print("These tests were designed to validate the tapestry version listed above.")
    dict_config = parse_config()
    dict_args = parse_args()
    if dict_args["do_network_tests"]:
        input("Start your FTP daemons for the network tests now, and press enter to continue.")
    if dict_args["runtime"]:
        print("Triggering the runtime tests. This can take quite a while depending on machine specs.")
        runtime_tests.runtime(dict_config)
    print("Starting the positive-case unit tests.")
    positive_tests.runtime(dict_config, dict_args["do_network_tests"])
    print("Starting the negative-case unit tests.")
    negative_tests.runtime(dict_config, dict_args["do_network_tests"])
    print("Tests complete. Logs would have output here: %s" % dict_config["path_logs"])
    exit(0)
