"""
This script is a component of the Tapestry project's testing framework.
Specifically, this component defines all the unit tests which constitute
positive controls; those whose outcome indicates something is designing
in an expected way. As a general rule new tests of this type should be
added into testing prior to the development of the corresponding
features. Ideally, coverage should be as high as possible with at least
one test for each function or class method in the program.

Author: Zac Adam-MacEwen (zadammac@kenshosec.com)
Tapestry is a product of Kensho Security Labs.
Produced under license.

Full license and documentation to be found at:
https://github.com/ZAdamMac/Tapestry
"""
from . import framework
import tapestry
from datetime import date
import hashlib
import os
import shutil
import time

__version__ = "2.1.0dev"
# Begin Function Definitions


def get_test_pkl(config, logger):
    """Call upon RecoveryIndex using a sample PKL file. Establishes
    whether or not the legacy recovery format (pre 2.0) can still be
    read by the version under test.

    :param config: a tapestry testing dict_config object.
    :param logger: the established logger object
    :return:
    """
    logger.log("-----------------------------[Pickle Load Test]-------------------------------")
    logger.log("This test establishes if the legacy archive format can still be parsed.")
    file_pkl = os.path.join(config["path_config"], os.path.join("test articles", "sample.psk"))
    try:
        rec_index = tapestry.RecoveryIndex(open(file_pkl, "r"))
        logger.log("[PASS] The recovery index object parsed the sample pickle file successfully.")
    except tapestry.RecoveryIndexError:
        logger.log("[FAIL] The recovery index object could not parse the target 'sample.pkl'. This\n"
                   "usually means there is an issue with the object itself as the sample pkl should\nnot have changed.")
        rec_index = False

    return rec_index


def get_test_riff(config, logger):
    """Call upon RecoveryIndex using a sample RIFF file. Establishes
    whether or not current-standard RIFF format can be read.

    :param config: a tapestry testing dict_config object.
    :param logger: the established logger object
    :return:
    """
    logger.log("-----------------------------[NewRIFF Load Test]------------------------------")
    logger.log("This test establishes if the standard archive format can still be parsed.")
    file_riff = os.path.join(config["path_config"], os.path.join("test articles", "sample.riff"))
    try:
        rec_index = tapestry.RecoveryIndex(open(file_riff, "r"))
        logger.log("[PASS] The recovery index object parsed the sample pickle file successfully.")
    except tapestry.RecoveryIndexError:
        logger.log("[FAIL] The recovery index object could not parse the target 'sample.riff'. This\n"
                   "usually means there is an issue with the object itself as the sample riff should\nnot have changed."
                   )
        rec_index = False

    return rec_index


def establish_logger(config):
    """Establish a logger to use for this test. Based on the SimpleLogger, so
    not actually appropriate for general use beyond this case.

    :param config: dict_config.
    :return: logger, a logging object.
    """
    name_log = ("runtime_test-%s-%s.log" % (config["test_user"], str(date.today())))
    logger = framework.SimpleLogger(config["path_logs"], name_log, "positive-tests")
    logger.log("----------------------------[Positive Unit Tests]-----------------------------")
    logger.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/Tapestry/__main__.py", "rb").read())
    taphash = hasher.hexdigest()
    logger.log("\n" + str(taphash) + "\n")
    logger.log("\nWhich relies on the classes library with hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/Tapestry/classes.py", "rb").read())
    taphash = hasher.hexdigest()
    logger.log("\n" + str(taphash) + "\n")

    return logger


def runtime(dict_config):
    """A simple runtime function that does the actual operating floor. This is
    what gets called from the main script in order to actually run the tests.

    :param dict_config: required, provides all config information.
    :return:
    """
    expects = ["test_user", "path_logs", "path_temp"]  # Add new dict_config keys here
    can_run = framework.validate_dict_config(dict_config, expects)
    if can_run:  # Any new tests need to be added here.
        log = establish_logger(dict_config)
        test_block = tapestry.Block("testblock", 100, 1, 0)
        test_block = test_block_valid_put(test_block, log)
        test_block_yield_full(test_block, log)
        riff_out = test_block_meta(dict_config, test_block, log)
        test_riff = get_test_riff(dict_config, log)
        test_riff_find(dict_config, test_riff, log)
        test_riff_compliant(dict_config, riff_out, log)
        test_pkl = get_test_pkl(dict_config, log)
        test_pkl_find(dict_config, test_pkl)
        test_TaskCheckIntegrity_call(dict_config, log)
        test_TaskCompress(dict_config, log)
        test_TaskDecompress(dict_config, log)
        test_TaskEncrypt(dict_config, log)
        test_TaskDecrypt(dict_config, log)
        test_TaskSign(dict_config, log)
        test_TaskTarBuild(dict_config, log)
        test_TaskTarUnpack(dict_config, log)
        test_generate_key(dict_config, log)
        test_build_ops_list(dict_config, log)
        test_build_recovery_index(dict_config, log)
        test_debug_print(dict_config, log)
        test_media_retrieve_files(dict_config, log)
        test_parse_config(dict_config, log)
        test_status_print(dict_config, log)
        test_verify_blocks(dict_config, log)
        log.save()
    else:
        print("Exiting the runtime tests as the config validity failed.")
        exit()


def test_block_meta(dict_config, block, logger):
    """Generates and places a RIFF file based on the meta() call. We use the
    resulting file later, so we return the path.

    :param dict_config:
    :param block:
    :param logger:
    :return:
    """
    file = block.name+'.riff'
    path_to_output_riff = os.path.join(dict_config["path_temp"], file)
    findex = {'fname': "test_file", 'sha256': "NaN", 'category': "test",
              'fpath': "/docs/test", 'fsize': 100
              }

    logger.log("------------------------[Block 'Meta' Method Tests]---------------------------")
    block.meta(1, 100, 1, str(date.today()), "This is just a test.", findex, dict_config["path_temp"])
    logger.log("[PASS]Didn't crash trying to place the file.")

    return path_to_output_riff


def test_block_valid_put(block, logger):
    """Attempts to place a file that would definitively fit in the block.
    The test "file" has been calculated in such a way that the block should
    also become full.

    :param dict_config: the configuration dictionary object.
    :param block: A Tapestry.classes.Block object.
    :param logger: The test's logger object.
    :return:
    """
    logger.log("------------------[Block Placement Test 1: Valid-Sized File]------------------")
    findex = {'fname': "test_file", 'sha256': "NaN", 'category': "test",
              'fpath': "/docs/test", 'fsize': 100
              }  # This mimics a generated file index entry.
    placed = block.put("test_file", findex)

    if not placed:
        logger.log("[FAIL] The block rejected this file in spite of the fact it was the correct\nsize.")
    else:
        logger.log("[PASS] The block correctly accepted the placement of this file.")

    return block


def test_block_yield_full(test_block, logger):
    """A very simple test to determine the state of the "full" attribute.

    :param test_block: The block unit under test
    :param logger: System logger
    :return:
    """
    logger.log("------------------[Block Placement Test 2: Check Full Flag]-------------------")
    if not test_block.full:
        logger.log("[FAIL] The block indicates it is not full. This is unexpected.")
    else:
        logger.log("[PASS] The block correctly identifies itself as full.")

# We don't want execution from main
if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(1)
