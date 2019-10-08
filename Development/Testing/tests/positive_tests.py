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
    name_log = ("positive_tests-%s-%s.log" % (config["test_user"], str(date.today())))
    logger = framework.SimpleLogger(config["path_logs"], name_log, "positive-tests")
    logger.log("----------------------------[Positive Unit Tests]-----------------------------")
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
                           os.path.join("config", "positive_tests.json")), "r") as f:
        dict_tests = json.load(f)

    # The following two lists should be populated with the function variables
    # Populate this list with all tests to be run locally.
    list_local_tests = [test_block_valid_put, test_block_yield_full, test_block_meta,
                        test_riff_find, test_riff_compliant, test_pkl_find,
                        test_TaskCheckIntegrity_call, test_TaskCompress, test_TaskDecompress,
                        test_TaskEncrypt, test_TaskDecrypt, test_TaskSign,
                        test_TaskTarBuild, test_TaskTarUnpack, test_build_ops_list,
                        test_build_recovery_index, test_media_retrieve_files,
                        test_parse_config, test_verify_blocks
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
        print("Exiting the positive tests as the config validity failed.")
        exit()


def test_block_meta(dict_config):
    """Generates and places a RIFF file based on the meta() call. We use the
    resulting file later, so we return the path.

    :param dict_config:
    :return:
    """
    block = tapestry.Block("test_block", 600, 1, 30)

    file = block.name+'.riff'
    path_to_output_riff = os.path.join(dict_config["path_temp"], file)
    findex = {'fname': "test_file", 'sha256': "NaN", 'category': "test",
              'fpath': "/docs/test", 'fsize': 100
              }
    block.put("test_file", findex)

    block.meta(1, 100, 1, str(date.today()), "This is just a test.", {"testfile": findex}, dict_config["path_temp"])

    if os.path.exists(path_to_output_riff):
        return []
    else:
        return ["[ERROR]The RIFF file appears not to have been placed."]


def test_block_valid_put(dict_config):
    """Attempts to place a file that would definitively fit in the block.
    The test "file" has been calculated in such a way that the block should
    also become full.

    :param dict_config: the configuration dictionary object.
    :return:
    """
    block = tapestry.Block("someblock", 100, 1, 0)
    findex = {'fname': "test_file", 'sha256': "NaN", 'category': "test",
              'fpath': "/docs/test", 'fsize': 100
              }  # This mimics a generated file index entry.
    placed = block.put("test_file", findex)

    if not placed:
        return["[ERROR] The block rejected this file in spite of the fact it was the correct size."]
    else:
        return []


def test_block_yield_full(test_block):
    """A very simple test to determine the state of the "full" attribute.

    :param test_block: The block unit under test
    :return:
    """
    block = tapestry.Block("none", 1, 1, 0)
    block.put("foo", {"fsize": 1})
    if not block.full:
        return["[FAIL] The block indicates it is not full. This is unexpected."]
    else:
        return []


def test_build_ops_list(config):
    """Bundled set of 5 tests which confirm operation of
    tapestry.build_ops_list(). Relies on just the config and log shared by all
    tests. Validates inclusive/exclusive behaviour, index completion, and both
    the set of keys used in each item's record in the recovery index as well
    as the validity of those values. Has an overall pass/fail flag as well.

    :param config:
    :return:
    """
    namespace = tapestry.Namespace()
    # We need a dummy namespace object. Not the whole thing, just enough.
    namespace.categories_default = ["a"]
    namespace.categories_inclusive = ["b"]
    namespace.inc = False
    namespace.category_paths = {"a": config["path_temp"],
                                "b": config["path_config"]}
    namespace.block_size_raw = 30000000  # Don't care at all.
    errors = []
    # This test is a special case where someone linked multiple tests into a
    # Single test object. Therefore rather than relying on test_case's traditional
    # reporting structure, we're flinging all logs into errors.

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
    foo, bar, file = [None, None, None]  # satisfy the linter.
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
        errors.append("[PASS] The overall count of a non-inclusive run matched the expected value.")
        validity["count_short"] = True
    else:
        errors.append("[FAIL] The overall count of a non-inclusive run did not match what was on disk")
    # is len test_ops_inc = len A+B?
    if len(test_ops_inc) == (count_short + count_long):
        errors.append("[PASS] The overall count of an inclusive run matched the expected value.")
        validity["count_long"] = True
    else:
        errors.append(
            "[FAIL] The overall count of an inclusive run did not match the expected value."
            "This likely indicates a failure to add the inclusive directories to the "
            "main run list.")

    del test_ops_inc  # We don't need this anymore and they can be weighty.
    # get first record.
    try:
        sample_item = test_ops_reg.popitem()[1]  # Get just the dictionary at the first key
    except KeyError:
        errors.append("Couldn't get a sample item - the ops list is empty!")
        return errors  # we can jump out of the function here, nothing else will pass.
    # These are all the keys expected in this index:
    expected = ["fname", "sha256", "category", "fpath", "fsize"]
    failed_keys = False  # For now.
    for key in expected:
        if key not in sample_item.keys():
            errors.append("[FAIL] Key `%s` is missing from the sample item. This won't likely recover." % str(key))
            failed_keys = True

    if not failed_keys:
        validity["all_keys"] = True
        errors.append("[PASS] All keys were found in the sample item as expected. This would recover.")

    # figure out where it is in reality.
    if not failed_keys:  # We need to have all the keys for this test.
        test_cat = sample_item["category"]
        path_origin = os.path.join(namespace.category_paths[test_cat],
                                   sample_item["fpath"])
        test_size = os.path.getsize(path_origin)
        test_hash = hashlib.sha256()
        with open(path_origin, "rb") as f:
            test_hash.update(f.read())
        if test_hash.hexdigest() == sample_item["sha256"]:
            errors.append("[PASS] The item referred to as a sample has the expected SHA256 Hash.")
            validity["test_hash"] = True
        else:
            errors.append("[FAIL] The item referred to has an unexpected SHA256 hash. Bad pathing?")
            errors.append("Actual Value: %s" % test_hash.hexdigest)
            errors.append("Expected Value: %s" % sample_item["sha256"])
        if test_size == sample_item["fsize"]:
            errors.append("[PASS] The item referred to as a sample has the expected overall size on disk.")
            validity["test_size"] = True
        else:
            errors.append("[FAIL] The item referred to has a sample has an unexpected size. Bad pathing?")

    # Finally, did everything pass?
    count_failed = 0
    for each in validity:
        if not validity[each]:
            count_failed += 1
    errors.append("\n")
    if count_failed <= 0:
        errors.append("[OVERALL PASS] All tests that are part of this set passed.")
    else:
        errors.append("[OVERALL FAIL] %s tests failed, therefore this set is considered failed."
                      % count_failed)

    return errors


def test_pkl_find(config):
    """Creates a recovery index from PKL and verifies that it can find an expected file.
    This is run against a loaded canonical riff to avoid a dependancy on
    earlier tests also having worked correctly.

    :param config: The global test configuration
    :return:
    """
    errors = []
    test_pkl_path = os.path.join(config["path_config"], os.path.join("test articles", "sample.psk"))
    with open(test_pkl_path, "rb") as f:
        try:
            test_pkl = tapestry.RecoveryIndex(f)
        except tapestry.RecoveryIndexError:
            errors.append("[ERROR] the sample file failed to unpack. This usually indicates that"
                          " the RecoveryIndex class cannot parse Pickle files correctly.")
            return errors
    try:
        result_category, result_path = test_pkl.find("testfile")
    except tapestry.RecoveryIndexError:
        errors.append("[ERROR]The PKL has loaded incorrectly - RecoveryIndexError!")
        result_category = "failed"
        result_path = "failed"

    if result_category == "test" and result_path == "/docs/test":
        pass  # we want the error list to remain len=0 to show the pass message.
    else:
        errors.append("[Error]The find method is returning values other than the expected:")
        errors.append("The current state of result_category was: %s" % result_category)
        errors.append("The current state of result_path was: %s" % result_path)

    return errors


def test_riff_compliant(config):
    """Provided a path to the RIFF file generated earlier, this will test it
    for structural validity. This is currently rather dumb logic: the present
    version does not allow for type validation.

    :param config:
    :return:
    """
    keys_expected_metarun = ["sumBlock", "sizeExtraLarge", "countFilesSum", "dateRec", "comment"]
    keys_expected_metablock = ["numBlock", "sizeLarge", "countFiles"]
    keys_expected_findex = ["fname", "sha256", "fsize", "fpath", "category"]
    do_metarun = True
    do_metablock = True
    do_findex = True

    errors = []
    test_riff_path = os.path.join(config["path_temp"], "test_block.riff")

    with open(test_riff_path, "r") as riff_file:
        unpacked_riff = json.load(riff_file)

    try:
        sample_metarun = unpacked_riff["metaRun"]
    except KeyError:
        errors.append('[ERROR] The "metaRun" attribute is missing from the RIFF. Without this, many'
                      ' future functions of Tapestry will fail. These failures can otherwise be '
                      'silent and are otherwise exposed only by testing.')
        do_metarun = False
        sample_metarun = {}
    try:
        sample_metablock = unpacked_riff["metaBlock"]
    except KeyError:
        errors.append('[ERROR] The "metaBlock" attribute is missing from the RIFF - this can lead to'
                      ' unexpected failures and may cause broken userland features in future releases.')
        do_metablock = False
        sample_metablock = {}
    try:
        sample_file_entry = unpacked_riff["index"]["testfile"]
    except KeyError:
        errors.append('[ERROR] The "index" attribute is missing. This will cause absolute failure of'
                      'recoverability for files generated with the current codebase.')
        do_findex = False
        sample_file_entry = {}

    if do_metarun:
        for key in keys_expected_metarun:
            try:
                value = sample_metarun[key]
                del value
            except KeyError:
                errors.append("[WARN] The %s attribute's %s key is absent." % ("metaRun", key))

    if do_metablock:
        for key in keys_expected_metablock:
            try:
                value = sample_metablock[key]
                del value
            except KeyError:
                errors.append("[WARN] The %s attribute's %s key is absent." % ("metaBlock", key))

    if do_findex:
        for key in keys_expected_findex:
            try:
                value = sample_file_entry[key]
                del value
            except KeyError:
                errors.append("[ERROR] The file index's %s key is unexpectedly absent. This will likely" % key)

    return errors


def test_build_recovery_index(config):
    """ Takes a known-size recovery index and makes sure it checks out.

    :param config: as usual
    :return:
    """
    errors = []
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
        errors.append("[ERROR] The sum_size value returned was unexpected. Should have been 3.")

    # We need to know the top file is the biggest - we'd expect that.
    biggest_file = test_index[0]

    if biggest_file == "file2":
        valid_index = True
    else:
        errors.append("[ERROR] The recovery index did not appear to be sorted by size correctly.")

    return errors


def test_riff_find(config):
    """Takes a test riff object and verifies that it can find an expected file.
    This is run against a loaded canonical riff to avoid a dependancy on
    earlier tests also having worked correctly.

    :param config:
    :return:
    """
    errors = []
    test_pkl_path = os.path.join(config["path_config"], os.path.join("test articles", "testblock.riff"))
    with open(test_pkl_path, "rb") as f:
        try:
            test_pkl = tapestry.RecoveryIndex(f)
        except tapestry.RecoveryIndexError:
            errors.append("[ERROR] the sample file failed to unpack. This usually indicates that"
                          " the RecoveryIndex class cannot parse RIFF files correctly.")
            return errors
    try:
        result_category, result_path = test_pkl.find("testfile")
    except tapestry.RecoveryIndexError:
        errors.append("[ERROR]The RIFF has loaded incorrectly - RecoveryIndexError!")
        result_category = "failed"
        result_path = "failed"

    if result_category == "test" and result_path == "/docs/test":
        pass  # we want the error list to remain len=0 to show the pass message.
    else:
        errors.append("[Error]The find method is returning values other than the expected:")
        errors.append("The current state of result_category was: %s" % result_category)
        errors.append("The current state of result_path was: %s" % result_path)

    return errors


def test_TaskCheckIntegrity_call(config):
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
    hasher.update(string_test.encode('utf-8'))
    control_hash = hasher.hexdigest
    test_file = os.path.join(dir_temp, "hash_test")
    test_tar = os.path.join(dir_temp, "test_tar")
    with open(test_file, "w") as f:
        f.write(string_test)

    with tarfile.open(test_tar, "w:") as tf:
        tf.add(test_file)

    # test_task = tapestry.TaskCheckIntegrity(test_tar, "hash_test", control_hash)
    # check_passed, foo = test_task()
    #del foo

    #if check_passed:
    #    pass
    #else:
    #    errors.append("[ERROR] The test article failed to pass TaskCheckIntegrity's test.")

    return errors


def test_TaskCompress(config):
    """Very simplistic test. Generate instance of TaskCompress and see if the
    output file goes where expected.

    :param config: dict_config
    :return:
    """
    errors = []
    target = os.path.join(config["path_temp"], "test_tar")
    expected = os.path.join(config["path_temp"], "test_tar.bz2")

    test_task = tapestry.TaskCompress(target, 1)
    test_task()
    if os.path.exists(expected):
        pass
    else:
        errors.append("[FAIL] Output file not found; was it created or is there a location error?")

    return errors


def test_TaskDecompress(config):
    """Decompression verified both in terms of whether or not compression
    detection is working, and whether or not the tarfile was changed as a
    result.

    :param config: dict_config
    :return:
    """
    errors = []
    target = os.path.join(config["path_temp"], "test_tar.bz2")
    control = os.path.join(config["path_temp"], "test_tar")
    hash_target = hashlib.sha256()
    hash_control = hashlib.sha256()
    with open(control, "rb") as c:
        hash_control.update(c.read())

    task_test = tapestry.TaskDecompress(target)
    result = task_test()

    if result.startswith("File"):
        errors.append("[FAIL] TaskDecompress incorrectly assumed this file was not compressed.")
    else:
        with open(target, "rb") as t:
            hash_target.update(t.read())
            if hash_target.hexdigest == hash_control.hexdigest:
                pass
            else:
                errors.append("[FAIL] TaskDecompress output a file with a different hash than the original.")

    return errors


def test_TaskDecrypt(config):
    """Decrypts a test file as previously generated, then validates it matches
    the original file.

    :param config:
    :return:
    """
    errors = []
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
                pass  # No change to errors is expected
            else:
                errors.append("[ERROR] Test file checksum mismatched with control; something's gone wrong.")
        else:
            errors.append("[ERROR] Test file was not present as expected.")
            errors.append("Response from TaskDecrypt: " % response)
    else:
        errors.append("[ERROR] No originating file. Did TaskEncrypt fail too?")

    return errors


def test_TaskEncrypt(config):
    """A simplistic test to confirm that the TaskEncrypt function behaves as
    expected. Because TaskDecrypt also has to be tested, decrypting the file
    as part of the test would be redundant and only slow testing.

    :param config:
    :return:
    """
    errors = []
    test_fp = config["test_fp"]
    temp = config["path_temp"]
    target = os.path.join(temp, "hash_test")
    os.rename(target, target+".tar")  # Necessary to get the tap.
    gpg = gnupg.GPG()
    test_task = tapestry.TaskEncrypt((target+".tar"), test_fp, temp, gpg)
    response = test_task()
    out_expected = target+".tap"

    if os.path.isfile(out_expected):
        pass  # doing this here leaves len(errors)=0, which is the test_case pass condition.
    else:
        errors.append("[ERROR] Test file is not found where expected.")
        errors.append("Response from TaskEncrypt: %s" % response)

    return errors


def test_TaskSign(config):
    """Simplistic test of the signing class. Simply checks to see the output
    goes as expected.

    :param config:
    :return:
    """
    errors = []
    temp = config["path_temp"]
    tgt = os.path.join(temp, "hash_test.tar")

    test_task = tapestry.TaskSign(tgt, config["test_fp"], temp, gnupg.GPG())
    response = test_task()

    if os.path.isfile(tgt+".sig"):
        pass  # doing this here leaves len(errors)=0, which is the test_case pass condition.
    else:
        errors.append("[ERROR] Test signature does not exist. See response from TaskSign below.")
        errors.append("Response: %s" % response)

    return errors


def test_TaskTarBuild(config):
    """Simplified test of the TaskTarBuild class's call.

    :param config:
    :return:
    """
    errors = []
    temp = config["path_temp"]
    tgt_old = os.path.join(temp, "hash_test.tar")
    tgt = os.path.join(temp, "hash_test")
    os.rename(tgt_old, tgt)
    shutil.copy(tgt, tgt+".bak")

    test_queue = mp.JoinableQueue()
    q_response = mp.JoinableQueue()
    test_task = tapestry.TaskTarBuild(tgt+".tar", "hash_test", tgt, "foo")
    test_queue.put(test_task)
    dict_locks = {}
    dict_locks.update({"foo": mp.Lock()})

    worker = tapestry.ChildProcess(test_queue, q_response,
                                   config["path_temp"], dict_locks, True)
    # we need to do this to provide the locks dictionary

    worker.start()  # So trigger the worker
    test_queue.join()  # And wait for it to complete

    response = q_response.get()
    test_queue.put(None)  # Poison pill to kill the child process.

    if os.path.exists(tgt+".tar"):
        pass  # doing this here leaves len(errors)=0, which is the test_case pass condition.
    else:
        errors.append("[ERROR] Test tarball was not created. See response from TaskTarBuild below.")
        errors.append("Response: " % response)

    return errors


def test_TaskTarUnpack(config):
    """Simplified test of the TaskTarUnpack class's call. Does hash validation
    to ensure that what was unpacked matches what was packed.

    :param config:
    :return:
    """
    errors = []
    temp = config["path_temp"]
    test_tarf = os.path.join(temp, "hash_test.tar")
    expected = os.path.join(temp, "unpacked")

    test_task = tapestry.TaskTarUnpack(test_tarf, "hash_test", temp, "unpacked")

    test_task()

    if os.path.isfile(expected):
        with open(os.path.join(temp, "hash_test.bak"), "rb") as f:
            hash_control = hashlib.sha256()
            hash_control.update(f.read())
        with open(expected, "rb") as f:
            hash_test = hashlib.sha256()
            hash_test.update(f.read())

        if hash_test.hexdigest == hash_control.hexdigest:
            pass  # doing this here leaves len(errors)=0, which is the test_case pass condition.
        else:
            errors.append("[ERROR] The file in question has changed from the original.")
    else:
        errors.append("[ERROR] The expected output file could not be located. Was an error thrown?")

    return errors


def test_media_retrieve_files(config):
    """This is a simple test that uses an expected pair of files to call the
    media_retrieve_files function from tapestry, then inspects the filesystem
    to see that those files were placed where expected. Finally, it examines
    the returned value (made_index) to make sure it is an instance of a
    RecoveryIndex object.

    This test relies on the existence of two files, "testtap.tap and
    testtap.tap.sig. These are provided for in the VCS and will exist if you
    simply cloned the repo. However, it's worth noting that these files really
    must be something that can be decrypted by a a key on the testing user's
    default keyring. This can either be the included test key file, or, if
    desired, a key generated by the testing user. In the latter case you must
    generate a new version of testtap.tap and testtap.tap.sig by:
    1 - Tarring the included recovery-riff file.
    2 - encrypting this as a message to the desired key, armoured out with the
    file name testtap.tap.
    3 - creating a detatched signature of that file, testtap.tap.sig, using
    any key.

    :param config:
    :return:
    """
    # We need a small, known-good tap with a known-good riff and sig to exist
    # in resources. This should be reflected in the documentation and the VCS
    # and the corresponding key also needs to be made public!
    errors = []

    test_index = tapestry.media_retrieve_files(config["path_config"], config["path_temp"], gnupg.GPG())
    found_tap = os.path.isfile(os.path.join(config["path_temp"], "testtap.tap"))
    found_sig = os.path.isfile(os.path.join(config["path_temp"], "testtap.tap.sig"))
    with open(os.path.join(config["path_config"],
                           os.path.join("test articles","testblock.riff")), "rb") as f:
        # This ACTUALLY suffices, tested robustly against similar objects.
        made_index = isinstance(test_index, type(tapestry.RecoveryIndex(f)))

    if not found_tap:
        errors.append("[ERROR] The %s file is not located in the working directory as expected." % "tap")
    if not found_sig:
        errors.append("[ERROR] The %s file is not located in the working directory as expected." % "sig")
    if not made_index:
        errors.append("[ERROR] media_retrieve_files did not return a RecoveryIndex object.")

    # we don't need an explicit pass statement because of how test_case works.

    return errors


def test_parse_config(ns):
    """Loads an expected control config file, running it through (parse_config),
    then performs validation against the resulting NS object.

    :param ns: the config argument for test_case
    :return:
    """
    errors = []
    arg_ns = tapestry.Namespace()
    arg_ns.config_path = os.path.join(ns["path_config"], os.path.join("test articles", "control-config.cfg"))
    parsed_conf = tapestry.parse_config(arg_ns)

    # we know the state of the control config, so you can use a static dict to validate
    dict_control = {
        "activeFP": "AAAA-AAAA-AAAA-AAAA-AAAA", "fp": "AAAA-AAAA-AAAA-AAAA-AAAA",
        "signing": True, "sigFP": "CCCC-CCCC-CCCC-CCCC-CCCC", "keysize": 2048,
        "compress": True, "compressLevel": 9, "step": "none", "sumJobs": 0,
        "jobsDone": 0, "modeNetwork": "sftp", "addrNet": "240.0.0.0", "portNet": 22,
        "nameNet": "amartian", "dirNet": "olympus mons/the face", "retainLocal": True,
        "block_size_raw": int(64 * 2 ** 20), "compid": "HAL 9000",
        "recovery_path": "The Obelisk", "uid": "anothermartian", "drop": "area51",
        "numConsumers": os.cpu_count(), "currentOS": platform.system()
        }

    # There are, however, dynamic constraints we have to test for
    if dict_control["currentOS"] == "Linux":
        catpaths = {"a": "nix_a", "b": "nix_b"}
        os_args = {
            "workDir": "/tmp/Tapestry/", "desktop": "/home/anothermartian/Desktop",
            "gpgDir": "/home/anothermartian/.gnupg", "categories_default": ["a"],
            "categories_inclusive": ["b"], "category_paths": catpaths
            }
        dict_control.update(os_args)
    elif dict_control["currentOS"] == "Windows":
        catpaths = {"a": "win_a", "b": "win_b"}
        os_args = {
            "workDir": "C:\\users\\anothermartian\\appdata\\local\\temp\\tapestry",
            "desktop": "C:\\Users\\anothermartian\\Desktop",
            "gpgDir": "C:\\Users\\anothermartian\\appdata\\roaming\\gnupg",
            "categories_default": ["a"], "categories_inclusive": ["b"],
            "category_paths": catpaths
            }
        dict_control.update(os_args)
    else:
        errors.append("[ERROR] Received unexpected value for for currentOS - "
                      "Are you on a supported platform?")
        return errors

    # Now, let's do this iteratively to make things simpler.
    dict_failures = {}
    for key in dict_control:
        try:
            result = parsed_conf.__getattribute__(key)
            if result != dict_control[key]:
                dict_failures.update({key: "did not have the expected value."})
        except AttributeError:
            dict_failures.update({key: "was not assigned."})

    # Finally, print the failures or passage
    if len(dict_failures) == 0:
        pass  # doing this here leaves len(errors)=0, which is the test_case pass condition.
    else:
        errors.append("[FAIL] The following errors were detected in the return:")
        for key in dict_failures:
            errors.append("[ERROR] %s %s" % (key, dict_failures[key]))

    return errors


def test_verify_blocks(config):
    """A highly simplified test for the verify_blocks functionality that relies
    on the same files as test_media_retrieve_files. Due to the nature of the
    verify_blocks function this requires human intervention - future work will
    be to include a bypass method to facilitate this test.

    :param config:
    :return:
    """

    errors = []
    ns = tapestry.Namespace()
    ns.workDir = os.path.join(config["path_config"], "test articles")

    results = tapestry.verify_blocks(ns, gpg_agent=gnupg.GPG(verbose=True), testing=True)

    if len(results) == 1:
        if results[0] == os.path.join(ns.workDir, "testtap.tap"):
            pass  # doing this here leaves len(errors)=0, which is the test_case pass condition.
        else:
            errors.append("[ERROR] An unexpected value was returned for the validity list: %s"
                          % results[0])
    elif len(results) == 0:
        errors.append("[ERROR] The verify_blocks function refused to validate the sample file."
                      "Verify that the blocks are validly signed and try again.")
    else:
        errors.append("[ERROR] verify_blocks returned an unexpected number of items. See response.")
        errors.append("Response: %s" % results)

    return errors


# We don't want execution from main
if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(1)
