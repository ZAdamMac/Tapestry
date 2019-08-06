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
import json
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


def runtime(dict_config, do_network):
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
        test_riff_find(test_riff, log)
        test_riff_compliant(riff_out, log)
        test_pkl = get_test_pkl(dict_config, log)
        test_pkl_find(test_pkl, log)
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
        if do_network:
            ftp_connection = test_ftp_connect(dict_config, log)
            test_ftp_deposit(dict_config, log, ftp_connection)
            test_ftp_grep(dict_config, log, ftp_connection)
            test_ftp_retrieve(dict_config, log, ftp_connection)
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
    block.meta(1, 100, 1, str(date.today()), "This is just a test.", {"testfile": findex}, dict_config["path_temp"])

    if os.path.exists(path_to_output_riff):
        logger.log("[PASS]Didn't crash trying to place the file.")
    else:
        logger.log("[FAIL]The RIFF file would appear not to have been placed.")

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


def test_riff_compliant(test_riff_path, logger):
    """Provided a path to the RIFF file generated earlier, this will test it
    for structural validity. This is currently rather dumb logic: the present
    version does not allow for type validation.

    :param test_riff_path:
    :param logger:
    :return:
    """
    logger.log("-------------------------[Riff Compliance Testing]----------------------------")
    keys_expected_metarun = ["sumBlock", "sizeExtraLarge", "countFilesSum", "dateRec", "comment"]
    keys_expected_metablock = ["numBlock", "sizeLarge", "sumFiles"]
    keys_expected_findex = ["fname", "sha256", "fsize", "fpath", "category"]
    do_metarun = True
    do_metablock = True
    do_findex = True

    with open(test_riff_path, "r") as riff_file:
        unpacked_riff = json.load(riff_file)

    try:
        sample_metarun = unpacked_riff["metaRun"]
    except KeyError:
        logger.log('[FAIL] The "metaRun" attribute is missing from the RIFF. Without this, many')
        logger.log('future functions of Tapestry will fail. These failures can otherwise be silent')
        logger.log('and are otherwise exposed only by testing.')
        do_metarun = False
        sample_metarun = {}
    try:
        sample_metablock = unpacked_riff["metaBlock"]
    except KeyError:
        logger.log('[FAIL] The "metaBlock" attribute is missing from the RIFF - this can lead to')
        logger.log('unexpected failures and may cause broken userland features in future releases.')
        do_metablock = False
        sample_metablock = {}
    try:
        sample_file_entry = unpacked_riff["index"]["testfile"]
    except KeyError:
        logger.log('[FAIL] The "index" attribute is missing. This will cause absolute failure of')
        logger.log('recoverability for files generated with the current codebase.')
        do_findex = False
        sample_file_entry = {}

    if do_metarun:
        for key in keys_expected_metarun:
            try:
                value = sample_metarun[key]
                del value
            except KeyError:
                logger.log("[WARN] The %s attribute's %s key is absent." % ("metaRun", key))

    if do_metablock:
        for key in keys_expected_metablock:
            try:
                value = sample_metablock[key]
                del value
            except KeyError:
                logger.log("[WARN] The %s attribute's %s key is absent." % ("metaBlock", key))

    if do_findex:
        for key in keys_expected_findex:
            try:
                value = sample_file_entry[key]
                del value
            except KeyError:
                logger.log("[FAIL] The file index's %s key is unexpectedly absent. This will likely" % key)


def test_riff_find(test_riff, logger):
    """Takes a test riff object and verifies that it can find an expected file.
    This is run against a loaded canonical riff to avoid a dependancy on
    earlier tests also having worked correctly.

    :param test_riff:
    :param logger:
    :return:
    """
    logger.log("----------------------------[Riff 'FIND' Test]--------------------------------")
    try:
        result_category, result_path = test_riff.find("testfile")
    except tapestry.RecoveryIndexError:
        logger.log("[FAIL]The Riff has loaded incorrectly - RecoveryIndexError!")
        result_category = "failed"
        result_path = "failed"

    if result_category == "test" and result_path == "/docs/test":
        logger.log("[PASS]The Find method returned the expected values based on the test RIFF.")
    else:
        logger.log("[FAIL]The find method is returning values other than the expected:")
        logger.log("The current state of result_category was: %s" % result_category)
        logger.log("The current state of result_path was: %s" % result_path)


# We don't want execution from main
if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(1)
