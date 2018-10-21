#! /usr/bin/python3.6
# Unit tests relating to Tapestry. Current as of 2.0.
# See the documentation - there are dependencies

# Import Block
import configparser
from datetime import date
from Development.Source import dev
from Development.Testing import framework as fw
import gnupg

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
    #goodRIFF is the string representation of a compliant RIFF structure.
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
    namespace.logger = fw.simpleLogger("Logs", namespace.filename, "unit-tests")

    return namespace


def import_for_keys(ns):
    """Check for the keys described in the namespace and adds them to the
    keyring if not present. Warns the user they should add this key to a trust
    level of minimal or higher for tests to work, and waits for them to do so.
    """
    found_enc_key = True
    found_sig_key = True
    list_present_keys = ns.gpg_instance.list_keys(True, keys=(ns.key_sign_fp, ns.key_crypt_fp))
    if len(list_present_keys) < 2: # We need to know which are missing.
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
        if not found_sig_key: # Without this sig tests fail.
            print("Importing the Test Signing Key")
            ns.gpg_instance.import_keys(open("test_sig_key", "r").read())
            print("In order to continue you should first escalate the trust of:")
            print("%s to at least Minimal" % ns.key_sign_fp)
            input("Press enter to continue.")


def test_config_compliance(ns):
    """Imports /Development/Source/Tapestry.cfg and parses it, then ensures
    that all the expected values are present. This test must be modified after
    development of the release is believed "finished" to ensure all values are
    present and correct.
    """
    pass


def test_encryption_cyclic(ns):
    """Test the encryption and decryption functions by providing a bytestream
    which acts as a dummy file. The input and output are compared."""
    pass


def test_inclusivity_diff(ns):
    """Runs the runlist creation process twice against both the regular and
    inclusive roots and makes sure the inclusive list is larger.
    """
    pass


def test_riff_compliance(ns):
    """This test compares the known-good RIFF (namespace.goodRIFF) to an RIFF
        generated by the runtime tests and extracted in the integrity test
        script to a known-correct position.
    """
    pass


def test_verification_good(ns):
    """Tests signing/verification against a bytes object, expecting a valid
    result.
    """
    pass


def test_verification_bad(ns):
    """Passes a known-badly-signed bytes object into the verification function to
    ensure that the function works as designed. This was necessary to prevent a
    recurrence of the verification bypass bug.
    """
    pass
