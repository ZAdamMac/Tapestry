#  Integrity Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules

def runtime():
    #  Parse test config
    permaHome = os.getcwd()

    cfg = cp.ConfigParser()
    cfg.read("tapestry-test.cfg")
    out = cfg.get("Environment Variables", "output path")
    uid = cfg.get("Environment Variables", "uid")
    host = cfg.get("Environment Variables", "compID")
    test_FTP_user = cfg.get("Network Configuration", "username")
    logs = os.path.join(permaHome, "Logs")
    blockSize = cfg.get("Environment Variables", "blocksize")

    #  Establish a Logger for Test Output
    if not os.path.isdir((logs)):
        os.mkdir(logs)

    logname = ("integrity_test-%s-%s.log" % (uid, str(date.today())))
    log = fw.simpleLogger(logs, logname, "integrity-tests")

    pathControl = out.replace("Test", "Control")

    print("\n\nStarting Identity Test")
    log.log("\n\n-------------------------------[INTEGRITY TESTS]-------------------------------")
    log.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
    hasher = hashlib.sha256()
    hasher.update(open("dev.py", "rb").read())
    taphash = hasher.hexdigest()
    log.log("\n"+str(taphash)+"\n")
    counterMismatch = 0
    identical = False

    for foo, bar, files in os.walk(os.path.join(pathControl,"Corpus")):
        for file in files:
            hashControl = hashlib.md5()
            hashTest = hashlib.md5()
            absfile = os.path.join(foo, file)
            testfile = absfile.replace("Control", "Test")
            with open(absfile, "rb") as f:
                hashControl.update(f.read())
            with open(testfile, "rb") as f:
                hashTest.update(f.read())

            if hashControl.hexdigest() != hashTest.hexdigest():
                print("Mismatch detected!")
                log.log("Mismatch detected in file: %s" % testfile)
                counterMismatch += 1

    if counterMismatch == 0:
        identical = True
        print("Identity test passed with no mismatching detected.")
        log.log("[PASSED] All files from the results of the recovery mode run were determined to \nmatch the original test corpus by means of md5 hash comparison.")
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
                        log.log("Signature mismatch in file: %s" % file)
                        failures =+ 1
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
                            decrypted = gpg.decrypt_file(k, always_trust=True, output=(os.path.join(out, "unpacked sample")))
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
            log.log("[PASSED] The decryption test was run - none of the test materials failed to\ndecrypt, which also validates that they were encrypted correctly.")
        else:
            log.log('''[FAILED] A total of %s files failed to decrypt as expected. This is most
    commonly caused by the loss of key material. Double-check this result manually
    using GPG to rule out an error in the cryptographic engine itself.''' % str(failures))
        log.log("-------------------------------------------------------------------------------")


    #  Version Specificity
    print("Beginning Recovery File Completion Check")
    log.log("\n\n------------------------[RECOVERY FILE STRUCTURE TEST]-------------------------")
    if identical:
        print("Decrypting a tapfile to run test against.")
        found = False
        for foo, bar, files in os.walk(out):
            if not found:
                for file in files:
                    if file.endswith(".tap"):
                        with open(os.path.join(foo, file), "rb") as k:
                            decrypted = gpg.decrypt_file(k, always_trust=True, output=(os.path.join(out, "unpacked sample")))
                            waiting = True
                        while waiting:
                            if decrypted.ok:
                                waiting = False
                            else:
                                continue

    print("Extracting recovery pickle from the tapfile.")
    tfTest = tarfile.open(os.path.join(out, "unpacked sample"))
    os.chdir(out)
    foo = tfTest.extract("recovery-pkl")

    pklControl = pickle.load(open(os.path.join(permaHome, "control-pkl"), "rb"))
    pklTest = pickle.load(open(os.path.join(out, "recovery-pkl"), "rb"))
    if len(pklControl) == len(pklTest):
        print("Recovery Files have Matching Structure!")
        log.log("[PASSED] No structural changes detected in the recovery file generated by the\ncode under test. This indicates that the version under test is non-breaking.")
    else:
        print("WARNING: Recovery Files are mismatched!")
        print("This could indicate a break in version compatibility.")
        log.log('''[FAILED] Structural changes were detected in the recovery file! This must be\n
    carefully inspected for the nature of such changes and error handling controls\n
    should be verified to avoid breaking reverse compatibility with older tapfiles.\n
    If you feel these changes were necessary, contact the project team for\n
    consultation on additional testing and approval.''')
    log.log("-------------------------------------------------------------------------------")

    #  Compression Testing
    print("Beginning Compression Efficacy Test!")
    log.log("\n\n--------------------------[COMPRESSION EFFICACY TEST]--------------------------")
    passing = True
    for foo, bar, files in os.walk(out):
        for file in files:
            if file.endswith(".tap"):
                size = os.path.getsize(os.path.join(foo, file))
                if int(size) > int(blockSize * ( 2 ** 20)):
                    print("Error: %s is larger than blocksize!" % file)
                    passing = False

    if passing:
        print("All tapfiles are smaller than the specified blocksize!")
        log.log("[PASSED] All files generated are smaller than their original blocksize.")
    else:
        print("Compression Efficacy Test failed. Check compression code or increase compression level.")
        log.log("[FAILED] One or more output blockfiles were larger than expected. Revise the\ncompression level setting and run again.")
    log.log("------------------------------------------------------------------------------")

    #Inclusive/Exclusive Differentiation Test
    sizePoolInclusive = 0
    sizePoolExclusive = 0

    print("Beginning Inclusive/Exclusive Size Test")
    log.log("\n\n------------------------[INCLUSIVE/EXCLUSIVE COMPARISON]-----------------------")
    for foo, bar, files in os.walk(os.path.join(out,"Non-Inc")):
        for file in files:
            sizePoolExclusive += os.path.getsize(os.path.join(foo, file))

    for foo, bar, files in os.walk(os.path.join(out,"Inc")):
        for file in files:
            sizePoolInclusive += os.path.getsize(os.path.join(foo, file))

    if sizePoolExclusive < sizePoolInclusive:
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
    os.chdir(os.path.join(out,"Non-Inc"))
    keysExpected = ["DR.key", "DRPub.key"]
    passing = True

    for key in keysExpected:
        if os.path.isfile(key):
            with open(key, "r") as k:
                keyIn = gpg.import_keys(k.read())
                if keyIn.count != 1:
                    print("Keys imported: %s count, expected 1." % keyIn.count)
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