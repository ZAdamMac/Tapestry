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
import gnupg
import hashlib
import json
import multiprocessing as mp
import os
from random import choice
from string import printable
import tarfile

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
    expects = ["test_user", "path_logs", "path_temp", "test_fp"]  # Add new dict_config keys here
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
        # test_generate_key(dict_config, log)
        # testing the above function would require an interaction bypass that
        # is not currently part of the 2.0.1 feature set.
        # FUTURE work will be to add that functionality.
        test_build_ops_list(dict_config, log)
        test_build_recovery_index(log)
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


def test_build_ops_list(config, log):
    """Bundled set of 5 tests which confirm operation of
    tapestry.build_ops_list(). Relies on just the config and log shared by all
    tests. Validates inclusive/exclusive behaviour, index completion, and both
    the set of keys used in each item's record in the recovery index as well
    as the validity of those values. Has an overall pass/fail flag as well.

    :param config:
    :param log:
    :return:
    """
    log.log("--------------------[Tests of the Build Ops List Function]--------------------")
    log.log("A series of internally-contained tests to test the build_ops_list function of")
    log.log("Tapestry/__main__.py. Can fail in a number of ways.")
    log.log("\n")
    namespace = tapestry.Namespace()
    # We need a dummy namespace object. Not the whole thing, just enough.
    namespace.categories_default = ["a"]
    namespace.categories_inclusive = ["b"]
    namespace.inc = False
    namespace.category_paths = {"a": config["path_temp"],
                                "b": config["path_config"]}
    namespace.block_size_raw = 30000000  # Don't care at all.

    # Argue to build ops list
    test_ops_reg = tapestry.build_ops_list(namespace)
    # and again with Inc.
    namespace.inc = True
    test_ops_inc = tapestry.build_ops_list(namespace)

    # validate the ops lists generated.
    # Assume invalid by default
    validity = {"count_short": False, "count_long": False, "all_keys": False,
                "test_hash": False, "test_size": False}
    # get a count of all items in directory "a"
    count_short = 0
    foo, bar, file = (None, None, None)  # satisfy the linter.
    for foo, bar, files in os.walk(namespace.category_paths["a"]):
        for file in files:
            count_short += 1
    del foo, bar, file
    # get count of items in "b"
    count_long = 0
    for foo, bar, files in os.walk(namespace.category_paths["b"]):
        for file in files:
            count_long += 1
    del foo, bar, file
    # is len test_ops_reg = len A?
    if len(test_ops_reg) == count_short:
        log.log("[PASS] The overall count of a non-inclusive run matched the expected value.")
        validity["count_short"] = True
    else:
        log.log("[FAIL] The overall count of a non-inclusive run did not match what was on disk")
    # is len test_ops_inc = len A+B?
    if len(test_ops_inc) == (count_short + count_long):
        log.log("[PASS] The overall count of an inclusive run matched the expected value.")
        validity["count_long"] = True
    else:
        log.log("[FAIL] The overall count of an inclusive run did not match the expected value")
        log.log("""       This likely indicates a failure to add the inclusive directories to the""")
        log.log("""       main run list.""")

    del test_ops_inc  # We don't need this anymore and they can be weighty.
    # get first record.
    try:
        sample_item = test_ops_reg.popitem()[1]  # Get just the dictionary at the first key
    except KeyError:
        log.log()  # Fail, nothing in the return!
        return  # we can jump out of the function here, nothing else will pass.
    # These are all the keys expected in this index:
    expected = ["fname", "sha256", "category", "fpath", "fsize"]
    failed_keys = False  # For now.
    for key in expected:
        if key not in sample_item.keys():
            log.log("[FAIL] Key `%s` is missing from the sample item. This won't likely recover." % str(key))
            failed_keys = True

    if not failed_keys:
        validity["all_keys"] = True
        log.log("[PASS] All keys were found in the sample item as expected. This would recover.")

    # figure out where it is in reality.
    if not failed_keys:  # We need to have all the keys for this test.
        test_cat = sample_item["category"]
        path_origin = os.path.join(namespace.category_paths[test_cat],
                                   sample_item["fpath"])
        test_size = os.path.getsize(path_origin)
        test_hash = hashlib.sha256()
        with open(path_origin, "rb") as f:
            test_hash.update(f.read())
        if test_size == sample_item["fsize"]:
            log.log("[PASS] The item referred to as a sample has the expected SHA256 Hash.")
            validity["test_hash"] = True
        else:
            log.log("[FAIL] The item referred to has an unexpected SHA256 hash. Bad pathing?")
        if test_size == sample_item["test_size"]:
            log.log("[PASS] The item referred to as a sample has the expected overall size on disk.")
            validity["test_size"] = True
        else:
            log.log("[FAIL] The item referred to has a sample has an unexpected size. Bad pathing?")

    # Finally, did everything pass?
    count_failed = 0
    for each in validity:
        if not validity[each]:
            count_failed += 1
    log.log("\n")
    if count_failed <= 0:
        log.log("[OVERALL PASS] All tests that are part of this set passed.")
    else:
        log.log("[OVERALL FAIL] %s tests failed, therefore this set is considered failed.")


def test_pkl_find(test_pkl, logger):
    """Takes a test riff object and verifies that it can find an expected file.
    This is run against a loaded canonical riff to avoid a dependancy on
    earlier tests also having worked correctly.

    :param test_pkl:
    :param logger:
    :return:
    """
    logger.log("----------------------------[PKL  'FIND' Test]--------------------------------")
    try:
        result_category, result_path = test_pkl.find("testfile")
    except tapestry.RecoveryIndexError:
        logger.log("[FAIL]The PKL has loaded incorrectly - RecoveryIndexError!")
        result_category = "failed"
        result_path = "failed"

    if result_category == "test" and result_path == "/docs/test":
        logger.log("[PASS]The Find method returned the expected values based on the test Pickle.")
    else:
        logger.log("[FAIL]The find method is returning values other than the expected:")
        logger.log("The current state of result_category was: %s" % result_category)
        logger.log("The current state of result_path was: %s" % result_path)


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


def test_build_recovery_index(log):
    """ Takes a known-size recovery index and makes sure it checks out.

    :param log: Simplelogger
    :return:
    """
    log.log("-------------------[Tests of Build Recovery Index Function]-------------------")
    log.log("Runs build_recovery_index() against a known 'ops list' object, then evaluates.")
    log.log("\n")
    recovery_index = {"file1": {
                                "fname": "b",
                                "fpath": "b",
                                "fsize": 1,
                                "sha256": "aabb",
                                "category": "a"
                               },
                      "file2": {
                                "fname": "b",
                                "fpath": "b",
                                "fsize": 2,
                                "sha256": "aabb",
                                "category": "a"
                                }
                      }
    test_index, sum_sizes = tapestry.build_recovery_index(recovery_index)

    valid_size = False
    valid_index = False

    if sum_sizes == 3:
        valid_size = True
    else:
        log.log("[FAIL] The sum_size value returned was unexpected. Should have been 3.")

    # We need to know the top file is the biggest - we'd expect that.
    biggest_file = test_index.pop()[0]

    if biggest_file == "file2":
        valid_index = True
    else:
        log.log("[FAIL] The recovery index did not appear to be sorted by size correctly.")

    if valid_index and valid_size:
        log.log("[PASS] All tests that are part of this set passed.")


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


def test_TaskCheckIntegrity_call(config, logs):
    """This test creates a random string, inserting it into a file, then
    tarring that file into a tarball in the temporary directory. The path to
    the tarfile and the hash of the random string are then provided to an
    instance of tapestry.TaskCheckIntegrity and the return value used to
    determine if the class is responding correctly.

    :param config: dict_config
    :param logs: logger
    :return:
    """
    logs.log("""
    -------------------------[Integrity Checker Test]-----------------------------
This test runs TaskCheckIntegrity for a known-good hash and ensures the logic
of the test is sound.""")
    dir_temp = config["path_temp"]
    string_test = ''.join(choice(printable) for i in range(2048))
    hasher = hashlib.sha256()
    hasher.update(string_test)
    control_hash = hasher.hexdigest
    test_file = os.path.join(dir_temp, "hash_test")
    test_tar = os.path.join(dir_temp, "test_tar")
    with open(test_file, "w") as f:
        f.write(string_test)

    with tarfile.open(test_tar, "w:") as tf:
        tf.add(test_file)

    test_task = tapestry.TaskCheckIntegrity(test_tar, "hash_test", control_hash)
    check_passed, foo = test_task()
    del foo

    if check_passed:
        logs.log("[PASS] The test article passed TaskCheckIntegrity as expected.")
    else:
        logs.log("[FAIL] The test article failed to pass TaskCheckIntegrity's test.")


def test_TaskCompress(config, log):
    """Very simplistic test. Generate instance of TaskCompress and see if the
    output file goes where expected.

    :param config: dict_config
    :param log: A SimpleLogger logger instance.
    :return:
    """
    log.log("------------------------------[Compression Test]------------------------------")
    log.log("A simple test to see if TaskCompress outputs a file as expected.")
    target = os.path.join(config["path_temp"], "test_tar")
    expected = os.path.join(config["path_temp"], "test_tar.bz2")

    test_task = tapestry.TaskCompress(target, "1")
    test_task()
    if os.path.exists(expected):
        log.log("[PASS] Found the zipped tarball where it was expected.")
    else:
        log.log("[FAIL] Output file not found; was it created or is there a location error?")


def test_TaskDecompress(config, log):
    """Decompression verified both in terms of whether or not compression
    detection is working, and whether or not the tarfile was changed as a
    result.

    :param config: dict_config
    :param log: SimpleLogger Logger object
    :return:
    """
    log.log("-----------------------------[Decompression Test]-----------------------------")
    log.log("Test some decompression functionality and ensure there's no changes to the tar")
    target = os.path.join(config["path_temp"], "test_tar.bz2")
    control = os.path.join(config["path_temp"], "test_tar")
    hash_target = hashlib.sha256
    hash_control = hashlib.sha256
    with open(control, "rb") as c:
        hash_control.update(c.read())

    task_test = tapestry.TaskDecompress(target)
    result = task_test()

    if result.startswith("File"):
        log.log("[FAIL] TaskDecompress incorrectly assumed this file was not compressed.")
    else:
        with open(target, "rb") as t:
            hash_target.update(t.read())
            if hash_target.hexdigest == hash_control.hexdigest:
                log.log("[PASS] Decompression fully successful without issues.")
            else:
                log.log("[FAIL] TaskDecompress output a file with a different hash than the original.")


def test_TaskDecrypt(config, log):
    """Decrypts a test file as previously generated, then validates it matches
    the original file.

    :param config:
    :param log:
    :return:
    """
    log.log("-------------------------------[Decryption Test]------------------------------")
    log.log("Tests TaskDecrypt and determines if the output file is conformant and present.")
    temp = config["path_temp"]
    target = os.path.join(temp, "hash_test.tap")

    if os.path.isfile(target):
        task_test = tapestry.TaskDecrypt(target, temp, gnupg.GPG())
        response = task_test()

        expected = target+".decrypted"

        if os.path.exists(expected):
            with open(os.path.join(temp,"hash_test.tar"), "rb") as f:
                hash_control = hashlib.sha256()
                hash_control.update(f.read())
            with open(expected, "rb") as f:
                hash_test = hashlib.sha256()
                hash_test.update(f.read())
            if hash_test.hexdigest == hash_control.hexdigest:
                log.log("[PASS] Test file exists as expected, and matches the original.")
            else:
                log.log("[FAIL] Test file checksum mismatched with control; something's gone wrong.")
        else:
            log.log("[FAIL] Test file was not present as expected.")
            log.log("Response: " % response)
    else:
        log.log("[ERROR] No originating file. Did TaskEncrypt fail too?")


def test_TaskEncrypt(config, log):
    """A simplistic test to confirm that the TaskEncrypt function behaves as
    expected. Because TaskDecrypt also has to be tested, decrypting the file
    as part of the test would be redundant and only slow testing.

    :param config:
    :param log:
    :return:
    """
    log.log("-------------------------------[Encryption Test]------------------------------")
    log.log("Tests TaskEncrypt and determines if it successfully generates an output file.")
    test_fp = config["test_fp"]
    temp = config["path_temp"]
    target = os.path.join(temp, "hash_test")
    os.rename(target, target+".tar")  # Necessary to get the tap.
    gpg = gnupg.GPG()
    test_task = tapestry.TaskEncrypt(target, test_fp, temp, gpg)
    response = test_task()
    out_expected = target+".tap"

    if os.path.isfile(out_expected):
        log.log("[PASS] Test file exists as expected.")
    else:
        log.log("[FAIL] Test file is not foud where expected.")
        log.log("Response from : %s" % response)


def test_TaskSign(config, log):
    """Simplistic test of the signing class. Simply checks to see the output
    goes as expected.

    :param config:
    :param log:
    :return:
    """
    log.log("--------------------------------[Signing Test]--------------------------------")
    log.log("Tests TaskSign and determines if a signature is present - signature will be")
    log.log("validated by a later test.")
    temp = config["path_temp"]
    tgt = os.path.join(temp, "hash_test.tar")

    test_task = tapestry.TaskSign(tgt, config["test_fp"], temp, gnupg.gpg())
    response = test_task()

    if os.path.isfile(tgt+".sig"):
        log.log("[PASS] Test signature exists where expected.")
    else:
        log.log("[FAIL] Test signature does not exist. See response from TaskSign below.")
        log.log("Response: %s" % response)


def test_TaskTarBuild(config, log):
    """Simplified test of the TaskTarBuild class's call.

    :param config:
    :param log:
    :return:
    """
    log.log("----------------------------[Unitary Tarring Test]----------------------------")
    log.log("Calls TaskTarBuild in order to add a single file to a single tarfile. Simply")
    log.log("validates that the tarfile was then created; a qualitative test of whether or")
    log.log("not the tarring was handled properly comes later.")
    temp = config["path_temp"]
    tgt_old = os.path.join(temp, "hash_test.tar")
    tgt = os.path.join(temp, "hash_test")
    os.rename(tgt_old, tgt)

    dict_locks = {}
    dict_locks.update({"foo": mp.Lock()})
    test_task = tapestry.TaskTarBuild(tgt+".tar", "hash_test", tgt, "foo")

    response = test_task()

    if os.path.exists(tgt+".tar"):
        log.log("[PASS] Test file found at the expected location.")
    else:
        log.log("[FAIL] Test tarball was not created. See response from TaskTarBuild below.")
        log.log("Response: " % response)


def test_TaskTarUnpack(config, log):
    """Simplified test of the TaskTarUnpack class's call. Does hash validation
    to ensure that what was unpacked matches what was packed.

    :param config:
    :param log:
    :return:
    """
    log.log("---------------------------[Unitary Untarring Test]---------------------------")
    log.log("Calls TaskTarUnpack to unpack a given tarfile and checks its contents against")
    log.log("a control of known value.")
    temp = config["path_temp"]
    test_tarf = os.path.join(temp, "hash_test.tar")
    expected = os.path.join(temp, "unpacked")

    test_task = tapestry.TaskTarUnpack(test_tarf, "hash_test", temp, "unpacked")

    test_task()

    if os.path.isfile(expected):
        with open(os.path.join(temp, "hash_test"), "rb") as f:
            hash_control = hashlib.sha256()
            hash_control.update(f.read())
        with open(expected, "rb") as f:
            hash_test = hashlib.sha256()
            hash_test.update(f.read())

        if hash_test.hexdigest == hash_control.hexdighest:
            log.log("[PASS] The test file matches its original contents. Validation via SHA256.")
        else:
            log.log("[FAIL] The file in question has changed from the original.")
    else:
        log.log("[FAIL] The expected output file could not be located. Was an error thrown?")

# We don't want execution from main
if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(1)
