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
    hasher.update(open("../../Source/tapestry/__main__.py", "rb").read())
    taphash = hasher.hexdigest()
    logger.log("\n" + str(taphash) + "\n")
    logger.log("\nWhich relies on the classes library with hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../../Source/tapestry/classes.py", "rb").read())
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
    expects = ["test_user", "path_logs", "path_temp", "test_fp", "sftp_id",
               "sftp_credential", "sftp_uid", "sftp_rootpath", "sftp_trust"]  # Add new dict_config keys here
    can_run = framework.validate_dict_config(dict_config, expects)

    # We're storing a lot of the externals of the testing in a config file.
    with open(os.path.join(dict_config["path_config"],
                           os.path.join("config", "negative_tests.json")), "r") as f:
        dict_tests = json.load(f)

    # The following two lists should be populated with the function variables
    # Populate this list with all tests to be run locally.
    list_local_tests = [test_block_invalid_put, test_verify_invalid_block,
                        test_recovery_index_invalid, test_decompress_uncompressed,
                        test_TaskCheckIntegrity]
    # Populate this list with all the network tests (gated by do_network)
    list_network_tests = [test_sftp_connect_invalid, test_sftp_connect_down, test_sftp_find,
                          test_sftp_place, test_sftp_fetch]

    if can_run:
        log = establish_logger(dict_config)
        skips = []
        if not os.path.exists(dict_config["path_temp"]):
            os.mkdir(dict_config["path_temp"])
        for test in list_local_tests:
            test_name = test.__name__
            try:
                test_dict = dict_tests[test_name]
                a = test_dict["title"]
                b = test_dict["description"]
                c = test_dict["pass message"]
                d = test_dict["fail message"]
                framework.test_case(dict_config, log, test, a, b, c, d)
            except KeyError:
                msg = "Test %s was undefined in the JSON file and skipped." % test_name
                print(msg)
                skips.append(msg)
            except AttributeError:
                msg = ("Test %s rose an attribute error: is the right function defined?"
                      % test_name)
                print(msg)
                skips.append(msg)

        if do_network:
            for test in list_network_tests:
                test_name = test.__name__
                try:
                    test_dict = dict_tests[test_name]
                    a = test_dict["title"]
                    b = test_dict["description"]
                    c = test_dict["pass message"]
                    d = test_dict["fail message"]
                    framework.test_case(dict_config, log, test, a, b, c, d)
                except KeyError:
                    msg = "Test %s was undefined in the JSON file and skipped." % test_name
                    print(msg)
                    skips.append(msg)
                except AttributeError:
                    msg = ("Test %s rose an attribute error: is the right function defined?"
                           % test_name)
                    print(msg)
                    skips.append(msg)
        for line in skips:
            log.log(line)
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


def test_TaskCheckIntegrity(config):
    """This test creates a random string, inserting it into a file, then
    tarring that file into a tarball in the temporary directory. The path to
    the tarfile and the hash of the random string are then provided to an
    instance of tapestry.TaskCheckIntegrity and the return value used to
    determine if the class is responding correctly.

    :param config: dict_config
    :return:
    """
    errors = []
    dir_temp = config["path_temp"]
    string_test = ''.join(choice(printable) for i in range(2048))
    hasher = hashlib.sha256()
    hasher.update("this is not right".encode('utf-8')) # We just want a nonsense hash.
    control_hash = hasher.hexdigest()
    test_file = os.path.join(dir_temp, "hash_test")
    test_tar = os.path.join(dir_temp, "test_tar")
    with open(test_file, "w") as f:
        f.write(string_test)

    with tarfile.open(test_tar, "w:") as tf:
        tf.add(test_file)

    test_task = tapestry.TaskCheckIntegrity(test_tar, "hash_test", control_hash)
    check_passed, foo = test_task()
    del foo

    if not check_passed:  # Since we passed in a known-bad hash, we can expect a failure.
        pass
    else:
        errors.append("[ERROR] The test article failed to pass TaskCheckIntegrity's test.")

    return errors


def test_sftp_connect_invalid(config):
    """A very simplistic test that validates a known-good set of SFTP
    information can be used to connect to a given SFTP endpoint and return a
    valid connection object. The errors returned by sftp_connect are added to
    the logger output, as is an error if the returned object is not an
    instance of the expected class. An improper trust value is supplied in
    order to ensure untrusted servers are connected.

    :param config:
    :return:
    """
    errors = []
    connection, resp_errors = tapestry.sftp_connect(config["sftp_id"], config["sftp_uid"],
                                                    config["sftp_credential"], "not_valid_trust")

    if connection:
        if isinstance(connection, tapestry.SFTPConnection):
            errors.append("[ERROR] sftp_connect returned a connection object, "
                          "which should not be the case.")
        else:
            errors.append("[ERROR] sftp_connect returned a connection that is"
                          " not an instance of the SFTPConnection class")

    return errors


def test_sftp_connect_down(config):
    """A very simplistic test that validates the response of SFTP_connect in
    the event that the target sftp server is non-responsive, by pointing to a
    server that does not exist.

    :param config:
    :return:
    """
    errors = []
    connection, resp_errors = tapestry.sftp_connect("8.8.8.8", config["sftp_uid"],
                                                    config["sftp_credential"], config["sftp_trust"])

    if connection:
        if isinstance(connection, tapestry.SFTPConnection):
            errors.append("[ERROR] sftp_connect returned a connection object, "
                          "which should not be the case.")
        else:
            errors.append("[ERROR] sftp_connect returned a connection that is"
                          " not an instance of the SFTPConnection class")

    return errors


def test_sftp_find(config):
    """This test checks if the sftp_find function correctly handles a case
    where the rootpath does not exist.

    :param config:
    :return:
    """
    errors = []

    connection, failure = tapestry.sftp_connect(config["sftp_id"], config["sftp_uid"],
                                                config["sftp_credential"], config["sftp_trust"])

    if not connection:
        errors.append("[ERROR] Connection attempt failed - did the previous test succeed?")
        return errors

    found, raised = tapestry.sftp_find(connection, config["sftp_rootpath"])

    if len(found) == 0:
        if raised.contains("directory"):
            pass
        else:
            errors.append("[ERROR] Raised %s" % raised)
    else:
        errors.append("[ERROR]Files were returned when they should not have been.")

    return errors


def test_sftp_place(config):
    """A quick test that attempts to place a copy of the test article
    "control-config.cfg" onto the SFTP server, in a location without write
    permissions.

    :param config:
    :return:
    """
    errors = []
    tgt_file = os.path.join(config["path_config"],
                            os.path.join("test articles", "control-config.cfg"))

    connection, failure = tapestry.sftp_connect(config["sftp_id"], config["sftp_uid"],
                                                    config["sftp_credential"], config["sftp_trust"])

    if not connection:
        errors.append("[ERROR] Connection attempt failed - did the previous test succeed?")
        return errors

    placed, raised = tapestry.sftp_place(connection, tgt_file, "unwriteable")

    if placed:
        errors.append("[ERROR] The file was placed when it should not have been. What went wrong?")

    return errors

def test_sftp_fetch(config):
    """A simple test to retreive a test file known to exist on the SFTP server,
     and place it into path_temp. Tests for success by checking that the file
    was actually placed.

    :param config:
    :return:
    """
    errors = []

    connection, failure = tapestry.sftp_connect(config["sftp_id"], config["sftp_uid"],
                                                config["sftp_credential"], config["sftp_trust"])

    if not connection:
        errors.append("[ERROR] Connection attempt failed - did the previous test succeed?")
        return errors

    raised = tapestry.sftp_fetch(connection, config["sftp_rootpath"], "not_real_file.txt",
                                 config["path_temp"])

    if raised:
        if not raised.startswith("404"):
            errors.append("[ERROR] Raised: %s" % raised)
    else:
        for root, dirs, found in os.walk(config["path_temp"]):
            if "control-file.txt" in found:
                errors.append("[ERROR] The find operation somehow returned a "
                              "file. How could this happen?")

    return errors

# We don't want execution from main
if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(1)
