"""
This script is a component of the Tapestry project's testing framework.
Specifically, this component defines all the full-runtime tests. These
are skipped for most commits but a requirement for the final code-
modifying commit prior to the packaging of a release PR.

Author: Zac Adam-MacEwen (zadammac@kenshosec.com)
Tapestry is a product of Kensho Security Labs.
Produced under license.

Full license and documentation to be found at:
https://github.com/ZAdamMac/Tapestry
"""

from . import framework
from datetime import date
import hashlib
import os
import shutil
import subprocess
import time

__version__ = "2.1.0dev"


def establish_logger(config):
    """Establish a logger to use for this test. Based on the SimpleLogger, so
    not actually appropriate for general use beyond this case.

    :param config: dict_config.
    :return: logger, a logging object.
    """
    name_log = ("runtime_test-%s-%s.log" % (config["test_user"], str(date.today())))
    logger = framework.SimpleLogger(config["path_logs"], name_log, "runtime-tests")
    logger.log("------------------------------[SAMPLE GENERATION]------------------------------")
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


def runtime(dict_config):
    """A simple runtime function that does the actual operating floor. This is
    what gets called from the main script in order to actually run the tests.

    :param dict_config: required, provides all config information.
    :return:
    """
    expects = ["test_user", "path_logs", "path_config", "path_corpus", "path_temp"]  # Add new dict_config keys here
    can_run = framework.validate_dict_config(dict_config, expects)
    if can_run:  # Any new tests need to be added here.
        log = establish_logger(dict_config)
        test_gen_key(dict_config, log)
        test_inc(dict_config, log)
        test_rcv(dict_config, log)
        delete = test_conformity(dict_config, log)
        log.save()
        if delete:
            shutil.rmtree(dict_config["path_temp"])
    else:
        print("Exiting the runtime tests as the config validity failed.")
        exit()


def test_conformity(config, logs):
    logs.log("-------------------------------[CHECK INTEGRITY]-------------------------------")

    failure = False

    for path_here, list_subdirs, files in os.walk(config["path_corpus"]):
        for file in files:
            hasher = hashlib.md5()
            path_origin = os.path.join(path_here, file)
            hasher.update(open(path_origin, "rb").read())
            hash_origin = hasher.hexdigest()

            hasher = hashlib.md5()
            path_placed = path_origin.replace(config["path_corpus"], config["path_temp"])
            try:
                hasher.update(open(path_placed, "rb").read())
                hash_test = hasher.hexdigest
            except FileNotFoundError:
                hash_test = b'0'

            if hash_origin != hash_test:
                failure = True

    if failure:
        print("[FAIL] Runtime Integrity Check Reveals mismatched or missing files.")
        logs.log("[FAIL] Runtime Integrity Check Reveals mismatched or missing files.")
    else:
        print("[PASS] Runtime Integrity Check validates files unpacked as expected.")
        logs.log("[PASS] Runtime Integrity Check validates files unpacked as expected.")

    return not failure


def test_gen_key(config, logs):
    """Test the genkey runtime without inclusivity, and put the subprocess
    output back into the logs. Relies on the "genkey-test.cfg" file in
    Testing/Resources/config.

    :param config:
    :param logs:
    :return:
    """
    config_this = os.path.join(config["path_config"], "/config/genkey-test.cfg")

    start = time.monotonic()
    waiting = subprocess.run(["python3.6", "-m", "tapestrydev", "--genKey", "--devtest", "-c", config_this])
    elapse = framework.elapsed(start)
    print("--genKey completed in %s" % elapse)
    logs.log("Key Generation Mode Test Completed in %s - Returned:" % elapse)
    logs.log(str(waiting))


def test_inc(config, logs):
    """Test the inclusive runtime, and put the subprocess
    output back into the logs. Relies on the "inc-test.cfg" file in
    Testing/Resources/config.

    :param config:
    :param logs:
    :return:
    """
    config_this = os.path.join(config["path_config"], "config/inc-test.cfg")

    start = time.monotonic()
    waiting = subprocess.run(["python3.6", "-m", "tapestrydev", "--inc", "--devtest", "-c", config_this])
    elapse = framework.elapsed(start)
    print("--inc completed in %s" % elapse)
    logs.log("Inclusive Mode Test Completed in %s - Returned:" % elapse)
    logs.log(str(waiting))


def test_rcv(config, logs):
    """Test the Recovery runtime, and put the subprocess output back
    into the logs. Relies on the "rcv-test.cfg" file in
    Testing/Resources/config. View the testdocs for details.

    :param config:
    :param logs:
    :return:
    """
    config_this = os.path.join(config["path_config"], "/config/rcv-test.cfg")

    start = time.monotonic()
    waiting = subprocess.run(["python3.6", "-m", "tapestrydev", "--inc", "--devtest", "-c", config_this])
    elapse = framework.elapsed(start)
    print("--rcv completed in %s" % elapse)
    logs.log("Recovery Mode Test Completed in %s - Returned:" % elapse)
    logs.log(str(waiting))


if __name__ == "__main__":
    print("This script is not intended to be run in standalone mode. Run main.")
    exit(0)
