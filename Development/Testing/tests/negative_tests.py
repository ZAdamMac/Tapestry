"""
This script is a component of the Tapestry project's testing framework.
Specifically, this component defines all the unit tests which constitute
negative controls, particularly in cases where the targeted function is
exposed to potentially-invalid inputs. As a general rule new tests of this type
should be added into testing prior to the development of the corresponding
features. Ideally, coverage should be as high as possible with at least
one test for each function or class method in the program which can be given an
invalid input from userland.

Author: Zac Adam-MacEwen (zadammac@kenshosec.com)
Tapestry is a product of Kensho Security Labs.
Produced under license.

Full license and documentation to be found at:
https://github.com/ZAdamMac/Tapestry
"""

from . import framework
import tapestry
from datetime import date
import gnupg
import hashlib
import json
import multiprocessing as mp
import os
import platform
from random import choice
import shutil
from string import printable
import tarfile

__version__ = "prototype"


def establish_logger(config):
    """Establish a logger to use for this test. Based on the SimpleLogger, so
    not actually appropriate for general use beyond this case.

    :param config: dict_config.
    :return: logger, a logging object.
    """
    name_log = ("negative_tests-%s-%s.log" % (config["test_user"], str(date.today())))
    logger = framework.SimpleLogger(config["path_logs"], name_log, "positive-tests")
    logger.log("----------------------------[Negative Unit Tests]-----------------------------")
    logger.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../../Source/Tapestry/__main__.py", "rb").read())
    taphash = hasher.hexdigest()
    logger.log("\n" + str(taphash) + "\n")
    logger.log("\nWhich relies on the classes library with hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../../Source/Tapestry/classes.py", "rb").read())
    taphash = hasher.hexdigest()
    logger.log("\n" + str(taphash) + "\n")

    return logger


def runtime(dict_config, do_network):
    """A simple runtime function that does the actual operating floor. This is
    what gets called from the main script in order to actually run the tests.

    :param dict_config: required, provides all config information.
    :param do_network: Boolean, controls if the network set are run.
    :return:
    """
    expects = ["test_user", "path_logs", "path_temp", "test_fp"]  # Add new dict_config keys here
    can_run = framework.validate_dict_config(dict_config, expects)

    # We're storing a lot of the externals of the testing in a config file.
    with open(os.path.join(dict_config["path_config"],
                           os.path.join("config", "negative_tests.json")), "r") as f:
        dict_tests = json.load(f)

    # The following two lists should be populated with the function variables
    # Populate this list with all tests to be run locally.
    list_local_tests = [test_block_invalid_put, test_verify_invalid_block,
                        test_recovery_index_invalid, test_decompress_uncompressed
                        ]
    # Populate this list with all the network tests (gated by do_network)
    list_network_tests = []
    # This list currently left blank as 2.0 network functionality is scrapped
    # entirely in 2.1's release and is unnecessary at this stage of development.

    if can_run:  # Any new tests need to be added here.
        log = establish_logger(dict_config)
        for test in list_local_tests:
            test_name = test.__name__
            try:
                test_dict = dict_tests[test_name]
                a = test_dict["title"]
                b = test_dict["description"]
                c = test_dict["pass message"]
                d = test_dict["fail message"]
                framework.test_case(dict_config, log, test, a, b, c, d)
            except KeyError as f:
                print("Test %s was undefined in the JSON file and skipped." % test_name)
                print(f)

        if do_network:
            for test in list_network_tests:
                test_name = test.__name__()
                try:
                    test_dict = dict_tests[test_name]
                    a = test_dict["title"]
                    b = test_dict["description"]
                    c = test_dict["pass message"]
                    d = test_dict["fail message"]
                    framework.test_case(dict_config, log, test, a, b, c, d)
                except KeyError:
                    print("Test %s was undefined in the JSON file and skipped.")
        log.save()
    else:
        print("Exiting the negative tests as the config validity failed.")
        exit()

# Tests Defined Below


def test_block_invalid_put(config):
    """Attempts to place a file that would definitively not fit in the block.

    :param dict_config: the configuration dictionary object.
    :return:
    """
    block = tapestry.Block("someblock", 100, 1, 0)
    findex = {'fname': "test_file", 'sha256': "NaN", 'category': "test",
              'fpath': "/docs/test", 'fsize': 101
              }  # This mimics a generated file index entry.
    placed = block.put("test_file", findex)

    if placed:
        return["[ERROR] The block accepted this file in spite of the fact it was the correct size."]
    else:
        return []


def test_decompress_uncompressed(config):
    """Attempts to decompress an uncompressed file. Fails if the expected
    rejection message is not returned.

        :param config: dict_config
        :return:
        """
    errors = []
    target = os.path.join(config["path_temp"], "hash_test.tar")

    task_test = tapestry.TaskDecompress(target)
    result = task_test()

    if not result.startswith("File"):
        errors.append("[FAIL] TaskDecompress incorrectly assumed this file was not compressed.")

    return errors


def test_recovery_index_invalid(config):
    """Attempts to load an unknown file. If no exception is raised, its
    not working correctly.

    :param config:
    :return:
    """
    errors = []
    target = os.path.join(config["path_temp"], "hash_test.tar")
    with open(target, "rb") as f:
        try:
            test_index = tapestry.RecoveryIndex(f)
            errors.append("[ERROR] RecoveryIndex did not raise the expected RecoveryIndexError exception.")
        except tapestry.RecoveryIndexError:
            pass
        finally:
            return errors


def test_verify_invalid_block(config):
    """A highly simplified test for the verify_blocks functionality that relies
        on the existance of a badly-signed file to check. Due to the nature of the
        verify_blocks function this requires human intervention - future work will
        be to include a bypass method to facilitate this test.

        :param config:
        :return:
        """

    errors = []
    ns = tapestry.Namespace()
    ns.workDir = os.path.join(config["path_config"], "test articles")

    results = tapestry.verify_blocks(ns, gpg_agent=gnupg.GPG(verbose=True), testing=True)

    if len(results) == 2:
       errors.append("[ERROR] The verify_blocks function accepted this invalid signature.")
    elif len(results) == 1:
        pass
    else:
        errors.append("[ERROR] verify_blocks returned an unexpected number of items. See response.")
        errors.append("Response: %s" % results)

    return errors

# We don't want execution from main
if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(1)
