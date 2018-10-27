#! /usr/bin/python3.6
# Unit tests relating to Tapestry. Current as of 2.0.
# See the documentation - there are dependencies

# Import Block
import configparser
from datetime import date
from Development.Source import dev
from Development.Testing import framework as fw
import gnupg
import json
import os
import hashlib

# Extra Classes Go Here

# Define Tests As Functions Here


def establish_namespace():
    """This function is best thought of as a general purpose config block and
    returns an object best thought of as a namespace object, used for ferrying
    configuration values around the program.
    """
    namespace = type('', (), {})()  # We need a general-purpose namespace object
    namespace.key_sign_fp = "3B5ACC53FE33CB690AF28AA2B1116E0BE39BA873"
    namespace.key_crypt_fp = "5EECD8B48E062B2520F518844C11667231468613"
    #  goodRIFF is the string representation of a compliant RIFF structure.
    namespace.goodRIFF = """{
  "metaBlock": {
    "numBlock": 1,
    "sizeLarge": 2000,
    "countFiles": 300
  },
  "metaRun":{
    "sumBlock": 1,
    "sizeExtraLarge": 2000,
    "countFilesSum": 300,
    "dateRec": 1540139133,
    "comment": "This is just a test RIFF."
  },
  "index":{
    "fidentifier": {
      "fname": "somefilename.png",
      "md5": "aefaf7502d52994c3b01957636a3cdd2",
      "category": "files",
      "fpath": "/go/to/somefilename.png",
      "fsize": 200
    }
  }
}
"""
    namespace.gpg_instance = gnupg.GPG()
    namespace.cfg = configparser.ConfigParser()
    namespace.cfg.read_file("tapestry-test.cfg")
    namespace.uid = namespace.cfg.get("Environment Variables", "uid")
    namespace.filename = "unit_test-" + str(namespace.uid) + "-" + str(date.today()) + ".log"
    namespace.logger = fw.SimpleLogger("Logs", namespace.filename, "unit-tests")
    namespace.failed_once = False  # Bool to show if any tests have failed.

    return namespace


def import_for_keys(ns):
    """Check for the keys described in the namespace and adds them to the
    keyring if not present. Warns the user they should add this key to a trust
    level of minimal or higher for tests to work, and waits for them to do so.
    """
    found_enc_key = True
    found_sig_key = True
    list_present_keys = ns.gpg_instance.list_keys(True, keys=(ns.key_sign_fp, ns.key_crypt_fp))
    if len(list_present_keys) < 2:  # We need to know which are missing.
        if ns.key_crypt_fp not in list_present_keys:
            found_enc_key = False
        if ns.key_sign_fp not in list_present_keys:
            found_sig_key = False
    if found_enc_key and found_sig_key:
        print("Found both testing keys.")
    else:
        if not found_enc_key:
            print("Importing the Test Encryption Key")
            ns.gpg_instance.import_keys(open("test_enc_key", "r").read())
            # No notification is required because this key does not need to be
            # trusted
            print("Done")
        if not found_sig_key:  # Without this sig tests fail.
            print("Importing the Test Signing Key")
            ns.gpg_instance.import_keys(open("test_sig_key", "r").read())
            print("In order to continue you should first escalate the trust of:")
            print("%s to at least Minimal" % ns.key_sign_fp)
            input("Press enter to continue.")
    return ns


def test_config_compliance(ns):
    """Imports /Development/Source/Tapestry.cfg and parses it, then ensures
    that all the expected values are present. This test must be modified after
    development of the release is believed "finished" to ensure all values are
    present and correct.
    """
    print("Beginning the Configuration Compliance Test")
    ns.logger.log()  # TODO populate log statements
    # First we need to know what we expect!
    expected_sections = ("Environment Variables", "Network Configuration",
                         "Additional Locations/Nix", "Default Locations/Nix",
                         "Additional Locations/Win", "Default Locations/Win")
    expected_ev_opts = ("uid", "compid", "blocksize", "expected fp", "keysize",
                        "sign by default", "signing fp", "recovery path",
                        "output path", "use compression", "compression level")
    expected_net_opts = ("mode", "server", "port", "username", "keep local copies" 
                         "remote drop location")
    found_ev = False
    found_net = False
    local_success = True  # For heuristics, we have to assume we succeeded.

    testparser = dev.parse_config(test=True)
    observed_sections = testparser.sections()

    # We need some found_ lists to work from!
    if "Environment Variables" in observed_sections:
        observed_ev_opts = testparser.options("Environment Variables")
        found_ev = True
    else:
        ns.logger.log()  # TODO populate log statements
        print("[FAIL] Environment Variables section missing from sample config.")
        ns.failed_once = True
        local_success = False
        observed_ev_opts = ()
    if "Network Configuration" in observed_sections:
        observed_net_opts = testparser.options("Network Configuration")
        found_net = True
    else:
        observed_net_opts = ()
        ns.logger.log()  # TODO Populate Log Statements.
        print("[FAIL] Network Configuration section missing from sample config.")
        ns.failed_once = True
        local_success = False

    # Now we know what we have and we can make sure it's what we want.
    for section in expected_sections:
        if section not in ("Environment Variables", "Network Configuration"):
            # We already looked for those!
            if section not in observed_sections:  # A Warning is Sufficient
                print("[WARN] %s section missing from sample config" % section)
                ns.logger.log()  # TODO Populate Log Statements
    if found_ev:
        for option in expected_ev_opts:
            if option not in observed_ev_opts:
                print("[FAIL] %s option missing from Environment Variables." % option)
                ns.logger.log()  # TODO populate log statements.
                ns.failed_once = True
                local_success = False
    if found_net:
        for option in expected_net_opts:
            if option not in observed_net_opts:
                print("[FAIL] %s option is missing from Network Configuration" % option)
                ns.logger.log()  # TODO populate log statements
                ns.failed_once = True
                local_success = False

    ns.config_test_pass = local_success
    ns.logger.log()  # TODO populate log statements
    print("End of Configuration Compliance Testing")
    return ns


def test_inclusivity_diff(ns):
    """Runs the runlist creation process twice against both the regular and
    inclusive roots and makes sure the inclusive list is larger.
    """
    ns.logger.log()
    short_list = dev.build_Ops_List("")
    long_list = dev.build_Ops_List("inc")
    if not (short_list < long_list):
        ns.failed_once = True
        ns.logger.log()  # TODO populate log statements
        ns.inclusivity_test_pass = False
        print("[FAIL] Inclusivity Test: Short List is Longer Than or Equal To Inclusive")
    else:
        ns.inclusivity_test_pass = True
        print("[PASS] Inclusivity Test - Lists are Expected Values")
        ns.logger.log()
    ns.logger.log()
    return ns


def test_riff_compliance(ns):
    """This test compares the known-good RIFF (namespace.goodRIFF) to an RIFF
        generated by the runtime tests and extracted in the integrity test
        script to a known-correct position.
    """
    print("Now beginning the RIFF Compliance Test")
    ns.logger.log()  # TODO populate log statements
    ns.riff_complaince_pass = True
    control_riff = json.loads(ns.goodRIFF)
    lab_output = ns.cfg.get("Environment Variables", "output")
    test_riff = json.load(os.path.join(lab_output, "index.riff"))
    found_top_keys = []  # Empty list we will use to hold the top-level keys we found.

    for key in control_riff:
        try:
            foo = test_riff[key]
            del foo
            found_top_keys.append(key)
        except KeyError:
            ns.failed_once = True
            ns.riff_complaince_pass = False
            print("[FAIL] Could not locate %s in the RIFF Sample." % key)
            ns.logger.log()  # TODO populate log statements

    for table in found_top_keys:
        if table is not "index":  # The index table is a special case.
            for column in control_riff[table]:
                try:
                    value = test_riff[table][column]
                    control_type = type(control_riff[table][column])
                    test_type = type(value)
                    if control_type != test_type:
                        print("[WARN] %s was found in the %s table, but is of an unexpected type" % (column, table))
                        ns.logger.log()  # TODO populate log statements.
                except KeyError:
                    print("[FAIL] %s was not found in the %s table." % (column, table))
                    ns.logger.log()  # TODO populate log statements
                    ns.failed_once = True
                    ns.riff_complaince_pass = False
        else:  # The index table is a really special case.
            index_table_test = test_riff[table]
            for column in control_riff[table][0]:  # The UUID would never match
                try:
                    value = index_table_test[0][column]
                    control_type = type(control_riff[table][column])
                    test_type = type(value)
                    if control_type != test_type:
                        print("[WARN] %s was found in the %s table, but is of an unexpected type" % (column, table))
                        ns.logger.log()  # TODO populate log statements.
                except KeyError:
                    print("[FAIL] %s was not found in the %s table." % (column, table))
                    ns.logger.log()  # TODO populate log statements
                    ns.failed_once = True
                    ns.riff_complaince_pass = False

    print("RIFF Compliance Test Complete.")
    ns.logger.log()  # TODO populate log statements
    return ns


def test_verification_good(ns):
    """Tests signing/verification against a bytes object, expecting a valid
    result.
    """
    gpg = ns.gpg_instance
    bytes_control = b"0XDEADBEEF"
    bytes_crypted = gpg.sign(bytes_control, keyid=ns.key_sign_fp)
    bytes_verified = dev.verify_block(bytes_crypted, test=True)

    if bytes_verified.ok:
        ns.test_verification_good_passed = True
        print("Sig Verification Test (Good) Passed!")
        ns.logger.log()  # TODO populate log statements
    else:
        ns.test_verification_good_passed = False
        print("Sig Verification Test (Good) Failed!")
        ns.logger.log()  # TODO populate log statements
    return ns


def test_verification_bad(ns):
    """Passes a known-badly-signed bytes object into the verification function to
    ensure that the function works as designed. This was necessary to prevent a
    recurrence of the verification bypass bug.
    """
    sig_bad_control = open("known_bad_sig.txt", "r").read()  # TODO generate and place.
    bytes_verified = dev.verify_block(sig_bad_control, test=True)

    if not bytes_verified.ok:
        ns.test_verification_bad_passed = True
        print("Sig Verification Test (Bad) Passed!")
        ns.logger.log()  # TODO populate log statements
    else:
        ns.test_verification_bad_passed = False
        print("Sig Verification Test (Bad) Failed!")
        ns.logger.log()  # TODO populate log statements
    return ns


# TODO add a strict verification check if using pinning (NOBLOCK)

def runtime():
    print("Now beginning the unit-tests for tapestry.")
    data = establish_namespace()
    data.logger.log("------------------------------[SAMPLE GENERATION]------------------------------")
    data.logger.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/dev.py", "rb").read())
    taphash = hasher.hexdigest()
    data.logger.log("\n"+str(taphash)+"\n")
    data = import_for_keys(data)
    data = test_config_compliance(data)
    data = test_inclusivity_diff(data)
    data = test_riff_compliance(data)
    data = test_verification_good(data)
    data = test_verification_bad(data)
    if data.failed_once:
        print("Some tests were failed. Please try again.")
        data.logger.log()  # TODO populate log strings
    else:
        print("All unit tests passed. Please try again.")
        data.logger.log()  # TODO populate log strings
