#  Integrity Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules

import os
import configparser as cp
from .framework import SimpleLogger
from datetime import date
import hashlib
import gnupg
import tarfile
import pickle


# noinspection PyUnusedLocal
def runtime():
    #  Parse test config
    perma_home = os.getcwd()

    cfg = cp.ConfigParser()
    cfg.read("tapestry-test.cfg")
    out = cfg.get("Environment Variables", "output path")
    uid = cfg.get("Environment Variables", "uid")
    logs = os.path.join(perma_home, "Logs")
    block_size = cfg.get("Environment Variables", "blocksize")

    #  Establish a Logger for Test Output
    if not os.path.isdir(logs):
        os.mkdir(logs)

    log_name = ("integrity_test-%s-%s.log" % (uid, str(date.today())))
    log = SimpleLogger(logs, log_name, "integrity-tests")

    path_control = out.replace("Test", "Control")

    print("\n\nStarting Identity Test")
    log.log("\n\n-------------------------------[INTEGRITY TESTS]-------------------------------")
    log.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/Tapestry/__main__.py", "rb").read())
    taphash = hasher.hexdigest()
    log.log("\n" + str(taphash) + "\n")
    log.log("\nWhich relies on the classes library with hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/Tapestry/classes.py", "rb").read())
    taphash = hasher.hexdigest()
    log.log("\n" + str(taphash) + "\n")

    counter_mismatch = 0
    identical = False

    for foo, bar, files in os.walk(os.path.join(path_control, "Corpus")):
        for file in files:
            hash_control = hashlib.md5()
            hash_test = hashlib.md5()
            absfile = os.path.join(foo, file)
            testfile = absfile.replace("Control", "Test")
            with open(absfile, "rb") as f:
                hash_control.update(f.read())
            with open(testfile, "rb") as f:
                hash_test.update(f.read())

            if hash_control.hexdigest() != hash_test.hexdigest():
                print("Mismatch detected!")
                log.log("Mismatch detected in file: %s" % testfile)
                counter_mismatch += 1

    if counter_mismatch == 0:
        identical = True
        print("Identity test passed with no mismatching detected.")
        log.log(
            "[PASSED] All files from the results of the recovery mode run were determined to \nmatch the original test corpus by means of md5 hash comparison.")
    else:
        identical = False
        print("Multiple Mismatches Detected - See the log for details.")
        log.log('''[FAILED] The identity test has passed failed as one or more files listed above  \n
    were determined via hash comparison not to match their original source files.   \n
    This sort of error is not acceptable in a file backup utility. See the testing  \n
    documentation for advice on possible causes of this failure.''')

        #  Encryption and Signing Passing
        # Test if Signatures are Valid
    gpg = gnupg.GPG(gnupghome=str("/home/" + uid + "/.gnupg"))
    print("Beginning Signature Verification.")
    log.log("\n\n-------------------------------[SIGNATURE TESTS]-------------------------------")
    failures = 0
    out = cfg.get("Environment Variables", "output path")
    os.chdir(out)
    for foo, bar, files in os.walk(out):
        for file in files:
            if file.endswith(".tap.sig"):
                with open(os.path.join(foo, file), "rb") as sig:
                    os.chdir(foo)
                    verified = gpg.verify_file(sig, file.rstrip(".sig"))
                    os.chdir(out)
                    if verified.trust_level is not None and verified.trust_level >= verified.TRUST_FULLY:
                        print("Signature at %s verified." % file)
                    else:
                        print("WARNING: Signature at %s insufficiently trusted." % file)
                        log.log("Signature mismatch in file: %s" % os.path.join(foo, file))
                        failures = + 1
    print("Signature verification completed with %s failures." % failures)
    if failures < 1:
        log.log('''[PASSED] All of the signatures compared in the signature testing were trusted,  \n
    and matched the expected value for their source document.                       \n''')
    else:
        log.log('''[FAILED] One or more signatures in this test were corrupt, absent, or not       \n
    sufficiently trusted. See the above for a list of failed signatures, and check  \n
    that your GPG instance considers the test signature key a trusted key.          \n''')

    log.log("-------------------------------------------------------------------------------")

    # If Identity failed, test encryption

    if identical:
        print("Decryption Test Skipped - Identity Check Passed.")
        log.log('''\n\n-----------------------------[ENCRYPTION TESTING]------------------------------\n
    [PASSED] Due to the passing of the Identity Test, it is not necessary to then\n
    test the cryptographic properties of the test blocks - their successful\n
    decryption is implied by the passage of the identity test.\n''')
    else:
        print("Beginning Decryption Test")
        log.log("\n\nBeginning Decryption Test")
        failures = 0
        first = True
        for foo, bar, files in os.walk(out):
            for file in files:
                if file.endswith(".tap"):
                    with open(file, "rb") as k:
                        if first:
                            decrypted = gpg.decrypt_file(k, always_trust=True,
                                                         output=(os.path.join(out, "unpacked sample")))
                            first = False
                        else:
                            decrypted = gpg.decrypt_file(k, always_trust=True)
                        if decrypted.ok:
                            print("Signature at %s verified." % file)
                        else:
                            print("WARNING: Decryption of %s failed because: %s" % (file, decrypted.ok_reason))
                            log.log("%s has failed to decrypt: %s" % (file, decrypted.ok_reason))
                            failures = + 1
        print("Decryption Testing completed with %s failures." % failures)
        if failures < 1:
            log.log(
                "[PASSED] The decryption test was run - none of the test materials failed to\ndecrypt, which also validates that they were encrypted correctly.")
        else:
            log.log('''[FAILED] A total of %s files failed to decrypt as expected. This is most
    commonly caused by the loss of key material. Double-check this result manually
    using GPG to rule out an error in the cryptographic engine itself.''' % str(failures))
        log.log("-------------------------------------------------------------------------------")

    # Version Specificity
    #print("Beginning Recovery File Completion Check")
    #log.log("\n\n------------------------[RECOVERY FILE STRUCTURE TEST]-------------------------")
    #if identical:
    #    print("Decrypting a tapfile to run test against.")
    #    found = False
    #    for foo, bar, files in os.walk(out):
    #        if not found:
    #            for file in files:
    #                if file.endswith(".tap"):
    #                   with open(os.path.join(foo, file), "rb") as k:
    #                        decrypted = gpg.decrypt_file(k, always_trust=True,
    #                                                     output=(os.path.join(out, "unpacked sample")))
    #                       waiting = True
    #                   while waiting:
    #                       if decrypted.ok:
    #                           waiting = False
    #                       else:
    #                           continue

    #print("Extracting recovery pickle from the tapfile.")
    #tf_test = tarfile.open(os.path.join(out, "unpacked sample"))
    #os.chdir(out)
    #print(tf_test.getmembers())
    #bar = tf_test.extract("recovery-riff")

    #pkl_control = pickle.load(open(os.path.join(perma_home, "control-pkl"), "rb"))
    #pkl_test = pickle.load(open(os.path.join(out, "recovery-riff"), "rb"))
    #if len(pkl_control) == len(pkl_test):
    #   print("Recovery Files have Matching Structure!")
    #   log.log(
    #       "[PASSED] No structural changes detected in the recovery file generated by the\ncode under test. This indicates that the version under test is non-breaking.")
    #else:
    #   print("WARNING: Recovery Files are mismatched!")
    #   print("This could indicate a break in version compatibility.")
    #   log.log('''[FAILED] Structural changes were detected in the recovery file! This must be\n
    #carefully inspected for the nature of such changes and error handling controls\n
    #should be verified to avoid breaking reverse compatibility with older tapfiles.\n
    #If you feel these changes were necessary, contact the project team for\n
    #consultation on additional testing and approval.''')
    #log.log("-------------------------------------------------------------------------------")

    #  Compression Testing
    print("Beginning Compression Efficacy Test!")
    log.log("\n\n--------------------------[COMPRESSION EFFICACY TEST]--------------------------")
    passing = True
    for foo, bar, files in os.walk(out):
        for file in files:
            if file.endswith(".tap"):
                size = os.path.getsize(os.path.join(foo, file))
                if int(size) > int(block_size * (2 ** 20)):
                    print("Error: %s is larger than blocksize!" % file)
                    passing = False

    if passing:
        print("All tapfiles are smaller than the specified blocksize!")
        log.log("[PASSED] All files generated are smaller than their original blocksize.")
    else:
        print("Compression Efficacy Test failed. Check compression code or increase compression level.")
        log.log("[FAILED] One or more output blockfiles were larger than"
                " expected. Revise the\ncompression level setting and run again.")
    log.log("------------------------------------------------------------------------------")

    # Inclusive/Exclusive Differentiation Test
    size_pool_inclusive = 0
    size_pool_exclusive = 0

    print("Beginning Inclusive/Exclusive Size Test")
    log.log("\n\n------------------------[INCLUSIVE/EXCLUSIVE COMPARISON]-----------------------")
    for foo, bar, files in os.walk(os.path.join(out, "Non-Inc")):
        for file in files:
            size_pool_exclusive += os.path.getsize(os.path.join(foo, file))

    for foo, bar, files in os.walk(os.path.join(out, "Inc")):
        for file in files:
            size_pool_inclusive += os.path.getsize(os.path.join(foo, file))

    if size_pool_exclusive < size_pool_inclusive:
        print("Inclusive/Exclusive Comparison Test Passed")
        log.log('''[PASSED] The output of the Inclusive Mode run was larger than the Key\n
    Generation Mode Run. This indicates that the inclusive mode is likely working\n
    correctly''')
    else:
        print("Inclusive/Exclusive sizes are mismatched!")
        log.log('''[FAILED] The output of the Inclusive Mode run was not larger than the Exclusive\n
    Mode Run. This indicates that the Inclusive Mode trigger is being ignored or\n
    there is a problem with adding the inclusive-run directories to the runlist.''')
    log.log("-------------------------------------------------------------------------------")

    #  Key Export Check
    print("Checking if keys were correctly exported!")
    log.log("\n\n---------------------------[KEY IMPORT/EXPORT TEST]----------------------------")
    os.chdir(os.path.join(out, "Non-Inc"))
    keys_expected = ["DR.key", "DRPub.key"]
    passing = True

    for key in keys_expected:
        if os.path.isfile(key):
            with open(key, "r") as k:
                key_in = gpg.import_keys(k.read())
                if key_in.count != 1:
                    print("Keys imported: %s count, expected 1." % key_in.count)
                    log.log("[FAILED] One or Both of the expected keyfiles were not present, or failed to\nimport.")
                    passing = False
                else:
                    print("%s imported successfully." % key)
    if passing:
        print("Keys were exported successfully!")
        log.log("[PASSED] The expected keyfiles were located and imported successfully.")
    else:
        print("Some keys did not pass correctly.")
    log.log("-------------------------------------------------------------------------------")
    log.save()


if __name__ == "__main__":
    runtime()
