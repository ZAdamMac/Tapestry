#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules
import argparse
import configparser as cp
from datetime import date
import dev
import ftplib as ftp
import gnupg
import hashlib
import json
import os
import pickle
import shutil
import ssl
import subprocess
import tarfile
import time


#  Stash classes and functions here if necessary.
class simpleLogger:  # dedicated skip-logging handler for use in buildBlocks
    def __init__(self, landingdir,name):  # starts the skiplogger and tells it it will be writing to landingdir with name
        landingAbs = os.path.join(landingdir, name)
        if not os.path.exists(landingdir):
            os.makedirs(landingdir)
        self.loggerfile = open(landingAbs, "w")  # This will REPLACE the existing logfile with the new one so be careful
        self.loggerfile.write("===============================================================================\nThis is a log of tests run against some version of Tapestry by the \nfunctional-tests.py testing utility. The date is indicated in the filename. \nIt should be made clear that these tests do not indicate any sort of warranty \nor guarantee of merchantability.\n\n=======TEST MACHINE SPECS=======\n")
        cores = os.cpu_count()
        self.loggerfile.write("Cores Available: %s \n" % cores)
        RAM = os.popen("free -m").readlines()[1].split()[1]
        self.loggerfile.write("RAM Available: %s MB \n" % RAM)
        self.loggerfile.write("================================\n\n\n\n================================BEGIN TESTING==================================\n")

    def log(self, foo):  # Formats foo nicely and adds it to the log
        self.loggerfile.write(foo + '\n')

    def save(self):  # saves the file to disk. Once used you have to re-instance the logger
        self.loggerfile.write("\n\n===============================[END OF TESTING]===============================")
        self.loggerfile.write("\n Tester Comments: ")
        self.loggerfile.write("\n This test was run on " + str(date.today()))
        self.loggerfile.flush()
        self.loggerfile.close()

def elapsed(start):  #Quickly calculate the elapsed time between two points, to feed to the logger. Returns it formatted nicely.
    current = time.monotonic()
    secElapsed = current - start
    strElapsed = time.strftime("%H:%M:%S", time.gmtime(secElapsed))
    return strElapsed

#  Parse test config
permaHome = os.getcwd()

cfg = cp.ConfigParser()
cfg.read("tapestry-test.cfg")
out = cfg.get("Environment Variables", "output path")
uid = cfg.get("Environment Variables", "uid")
host = cfg.get("Environment Variables", "compID")
test_FTP_user = cfg.get("Network Configuration", "username")
test_FTP_pw = input("Enter password for FTP testing: ")
logs = os.path.join(permaHome, "Logs")
blockSize = cfg.get("Environment Variables", "blocksize")

shutil.copy("tapestry-test.cfg", "tapestry-test.cfg.bak") # We create a backup of the config to restore to after testing.

pathControl = out.replace("Test", "Control")

gpg = gnupg.GPG(gnupghome=str("/home/" + uid + "/.gnupg"))

parser = argparse.ArgumentParser(description="Testing Framework for development of Tapestry Specialist Backup Tool")
parser.add_argument('--ssg', help="Skip sample generation. Invalidates test, but useful for debugging new tests.", action="store_true")
args = parser.parse_args()
ssg = args.ssg

#  Establish a Logger for Test Output
if not os.path.isdir((logs)):
    os.mkdir(logs)

logname = ("test-%s-%s.log" % (uid, str(date.today())))
log = simpleLogger(logs, logname)


#  Do the bulk runs and context switching to generate the test outputs (make sure to seperate outputs between runs!)
log.log("------------------------------[SAMPLE GENERATION]------------------------------")
if not ssg:
    cfg.set("Environment Variables", "output path", os.path.join(out, "Non-Inc"))
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)
    if not os.path.isdir(os.path.join(out, "Non-Inc")):
        os.mkdir(os.path.join(out, "Non-Inc"))
    print("Now Beginning the --genKey test")
    start = time.monotonic()
    waiting = subprocess.run(("python3.6", "dev.py", "--genKey"))
    elapse = elapsed(start)
    print("--genKey completed in %s" % elapse)
    log.log("Key Generation Mode Test Completed in %s - Returned:" % elapse)
    log.log(str(waiting))

    cfg.set("Environment Variables", "output path", os.path.join(out, "Inc"))
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)

    print("Now beginning --inc test.")
    start = time.monotonic()
    waiting = subprocess.run(("python3.6", "dev.py", "--inc"))
    elapse = elapsed(start)
    print("--inc completed in %s" % elapse)
    log.log("Inclusive Backup Mode Test Completed in %s - Returned:" % elapse)
    log.log(str(waiting))

    cfg.set("Environment Variables", "output path", os.path.join(out,"Corpus"))
    cfg.set("Environment Variables", "recovery path", os.path.join(out, "Inc"))
    docs = cfg.get("Default Locations/Nix", "docs")
    cfg.set("Default Locations/Nix", "docs", docs.replace("Control", "Test"))
    pics = cfg.get("Default Locations/Nix", "photos")
    cfg.set("Default Locations/Nix", "photos", pics.replace("Control", "Test"))
    vids = cfg.get("Additional Locations/Nix", "video")
    cfg.set("Additional Locations/Nix", "video", vids.replace("Control", "Test"))
    cfg.remove_option("Additional Locations/Nix", "Music") # This should still wind up in corpus if you didn't break directionless recovery.
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)

    print("Now beginning --rcv test.")
    start = time.monotonic()
    waiting = subprocess.run(("python3.6", "dev.py", "--rcv"))
    elapse = elapsed(start)
    print("--rcv completed in %s" % elapse)
    log.log("ecovery Mode Test Completed in %s - Returned:" % elapse)
    log.log("%s" % waiting)

    shutil.copy("tapestry-test.cfg.bak", "tapestry-test.cfg")
    print("Sample generation complete!")
else:
    print("Skipping Sample Generation. This test is not valid.")
    log.log("""In this instance the Sample Generation stage of testing was skipped. This is    \n
usually done to enable developers to test the testing framework itself. As most \n
of the tests are designed to run against a freshly-generated sample corpus, in  \n
order to verify that the functions used to create that corpus are working as    \n
intended, this test is not considered valid for purposes of merging a PR to the \n
Master branch. This feature is included only to facilitate testing of newly-    \n
added tests for features which are to be added to the test corpus. See the test \n
documents for details.""")
log.log("-------------------------------------------------------------------------------")

#  Identity Testing -- Hash to Hash
print("\n\nStarting Identity Test")
log.log("\n\n-------------------------------[INTEGRITY TESTS]-------------------------------")
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
print("Signature verification completed with %s failures." % failures) # TODO fix for pass/fail
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
                    if decrypted.ok:
                        pass
print("Extracting recovery pickle from the tapfile.")
tfTest = tarfile.open(os.path.join(out, "unpacked sample"))
os.chdir(out)
tfTest.extract("recovery-pkl")

pklControl = pickle.load(open(os.path.join(pathControl, "control-pkl"), "rb"))
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
for foo, bar, file in os.walk(os.path.join(out,"Non-Inc")):
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

# Certificate Check Tests
print("Beginning Networking Tests")
log.log("\n\n-------------------------[NETWORK CONNECTIVITY TESTS]--------------------------")
os.chwd(permaHome)

# We use popen not to block the test script while the servers are running, but we need to close them later, so we catch the processes in some vars.
srvBad = subprocess.Popen(args="vsftpd vsftpd-bad.config", shell=True, stdout=subprocess.DEVNULL)
srvGood = subprocess.Popen(args="vsftpd vsftpd-good.config.py", shell=True, stdout=subprocess.DEVNULL)

#Test the Bad Link First
testcontext = ssl.SSLContext().load_verify_locations(cafile="testcert.pem")

try:
    instFTP = dev.connectFTP("localhost", 21, testcontext, test_FTP_user, test_FTP_pw)
    print("Malicious Connection Test - FAIL - Connection Accepted.")
    log.log("[FAILED] Tapestry connected to the 'malicious' server and accepted it as a\nlegitimate connection.")
except ConnectionRefusedError:  # This should hopefully be the right exception but some offline tests are required
    print("Malicious Connection Test - PASS - Connection Refused.")
    log.log("[PASSED] The 'malicious' server was correctly rejected by Tapestry's connection\nestablishment function.")

srvBad.terminate()

#Now the Good Link

try:
    instFTP = dev.connectFTP("localhost", 21, testcontext, test_FTP_user, test_FTP_pw)
    print("Benign Connection Test - PASS - Connection Accepted.")
    log.log("[PASSED] The 'valid' server was accepted by the connection establishment\nfunction and a valid connection object is being passed to the next test.")
except ConnectionRefusedError:  # This should hopefully be the right exception but some offline tests are required
    print("Benign Connection Test - FAIL - Connection Refused.")
    log.log("[FAILED] The 'valid' server was rejected by the connection establishment\nfunction and the next test must be skipped.")
log.log("-------------------------------------------------------------------------------")

#Transfer Tests
log.log("\n\n--------------------------[NETWORK PUSH/PULL TEST]-----------------------------")
if instFTP is None:
    print("Skipping Transfer Tests - No FTP Connection could be Established.")
    log.log("[FAILED] The network transfer tests could not be passed as no connection was\nestablished. Verify that vsftpd is configured correctly on the test machine and\nthat tapestry-test.cfg contains the correct credentials for the FTP test user.")
else:
    print("Beginning file transfer tests using inert transfer article.")
    dev.sendFile(instFTP, "testblock-2001-01-01.txt")
    countPlaced, listPlaced = dev.grepBlocks("testblock", "2001-01-01", instFTP)
    dev.fetchBlock("testblock.txt", instFTP, "/")
    hashControlFTP = hashlib.md5().update(open("testblock.txt", "rb").readall())
    hashRelayFTP = hashlib.md5().update(open(os.path.join(out, "testblock.txt")).readall())
    if hashRelayFTP == hashControlFTP:
        print("File Transfer Success")
        log.log("[PASSED] A file was successfully uploaded to the test server, retrieved, and\ncompared to the original file by its md5 hash.")
    else:
        print("Error in File Transfer - Hashes Don't Match")
        print("Retrieve the testblock.txt file from the FTP server for comparison.")
        log.log("[FAILED] A file which was uploaded to the test server, and subsequently\nretrieved, did not match its original condition. Test this manually to ensure\nno problem exists in vsftpd and then re-examine the transfer functions in\nTapestry.")
    if countPlaced == 1 and listPlaced == ["testblock-2001-01-01.txt"]:
        print("grepBlocks works for FTP")
        log.log("[PASSED] The function to search by label and date on the server is working.")
    else:
        print("grepBlocks returned either the wrong count or list.")
        log.log("[FAILED] The FTP search function is not operating correctly. It will not be \npossible to retrieve files from the FTP site at present.")
log.log("------------------------------------------------------------------------------")

#  Clear Down!
log.save()

print("After passing this confirmation screen, the test result material will be deleted (except the log), including files on the FTP server. If you need to dissect further, leave this session open or delete the items manually yourself.")
carryOn = input("Press any key to continue. > ")
shutil.rmtree(out)
if instFTP is not None:
    instFTP.delete("testblock.txt")
srvGood.terminate()
remKey = gpg.delete_keys(cfg.get("Environment Variables", "Expected FP"), secret=True, expect_passphrase=False)
remKey = gpg.delete_keys(cfg.get("Environment Variables", "Expected FP"))
