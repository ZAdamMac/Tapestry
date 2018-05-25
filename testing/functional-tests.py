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
        self.loggerfile.write("This is a log of tests run against some version of tapestry by the functional-tests.py testing utility. \n")
        self.loggerfile.write("\n\n\n")
        self.loggerfile.write("===============")
        global host
        self.loggerfile.write("\nTest Host: %s \n" % host)
        cores = os.cpu_count()
        self.loggerfile.write("Cores Available: %s \n" % cores)
        RAM = os.popen("free -m").readlines()[1].split()[1]
        self.loggerfile.write("RAM Available: %s MB \n" % RAM)
        self.loggerfile.write("===============\n\n\n\n[Tests Begin - Generating Samples]\n")

    def log(self, foo):  # Formats foo nicely and adds it to the log
        self.loggerfile.write(foo + '\n')

    def save(self):  # saves the file to disk. Once used you have to re-instance the logger
        self.loggerfile.write("\n")
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
if not ssg:
    cfg.set("Environment Variables", "output path", os.path.join(out, "Non-Inc"))
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)
    if not os.path.isdir(os.path.join(out, "Non-Inc")):
        os.mkdir(os.path.join(out, "Non-Inc"))
    log.log("Now beginning the --genKey test.")
    print("Now Beginning the --genKey test")
    start = time.monotonic()
    waiting = subprocess.run(("python3.6", "dev.py", "--genKey"))
    elapse = elapsed(start)
    print("--genKey completed in %s" % elapse)
    log.log("--genKey completed in %s" % elapse)
    log.log("Run returned with the following information: %s" % waiting)

    cfg.set("Environment Variables", "output path", os.path.join(out, "Inc"))
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)

    print("Now beginning --inc test.")
    log.log("Now beginning --inc test.")
    start = time.monotonic()
    waiting = subprocess.run(("python3.6", "dev.py", "--inc"))
    elapse = elapsed(start)
    print("--inc completed in %s" % elapse)
    log.log("--inc completed in %s" % elapse)
    log.log("--inc returned the following information: %s" % waiting)

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
    log.log("--rcv completed in %s" % elapse)
    log.log("--rcv returned the following information: %s" % waiting)

    shutil.copy("tapestry-test.cfg.bak", "tapestry-test.cfg")
    print("Sample generation complete!")
else:
    print("Skipping Sample Generation. This test is not valid.")
    log.log("Invalid Test: Sample Generation Was Skipped.")

#  Identity Testing -- Hash to Hash
print("\n\nStarting Identity Test")
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
            log.log("Mismatch detected with file: %s" % testfile)
            counterMismatch += 1

if counterMismatch == 0:
    identical = True
    print("Identity test passed with no mismatching detected.")
    log.log("Identity test passed with no mismatching detected.")
else:
    identical = False
    print("Multiple Mismatches Detected - See the log for details.")
    log.log("Identity test failed.")

#  Encryption and Signing Passing
    # Test if Signatures are Valid
print("Beginning Signature Verification.")
log.log("\n\nBeginning of Signature Verification Test.")
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
                    log.log("%s has failed verification: insufficient trust." % file)
                    failures =+ 1
print("Signature verification completed with %s failures." % failures)
log.log("Signature Verification Test complete. In total there were %s failures." % failures)

    # If Identity failed, test encryption
if identical:
    print("Decryption Test Skipped - Identity Check Passed.")
    log.log("\n\nSkipping Decryption Test - The Identity Check implicitly passed it.")
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
    log.log("Decryption Test complete. In total there were %s failures." % failures)

#  Version Specificity
print("Beginning Recovery File Completion Check")
log.log("\n\n\nBeginning Recovery File Comparison")
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
    log.log("No changes detected in recovery-pkl structure.")
else:
    print("WARNING: Recovery Files are mismatched!")
    print("This could indicate a break in version compatibility.")
    log.log("Pickle Comparison Failed: Test case does not match control. Possible break in version compatibility. Please test manually.")

#  Compression Testing
print("Beginning Compression Efficacy Test!")
log.log("\n\n\nBeginning Compression Efficacy Test")
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
    log.log("Compression Efficacy Test Passed")
else:
    print("Compression Efficacy Test failed. Check compression code or increase compression level.")
    log.log("Compression Efficacy Test Failed. Check compression code or increase compression level.")

#Inclusive/Exclusive Differentiation Test
sizePoolInclusive = 0
sizePoolExclusive = 0

print("Beginning Inclusive/Exclusive Size Test")
for foo, bar, file in os.walk(os.path.join(out,"Non-Inc")):
    for file in files:
        sizePoolExclusive += os.path.getsize(os.path.join(foo, file))

for foo, bar, files in os.walk(os.path.join(out,"Inc")):
    for file in files:
        sizePoolInclusive += os.path.getsize(os.path.join(foo, file))

if sizePoolExclusive < sizePoolInclusive:
    print("Inclusive/Exclusive Comparison Test Passed")
    log.log("Passed!")
else:
    print("Inclusive/Exclusive sizes are mismatched!")
    log.log("Failed: Exclusive run produced equal or larger output to the inclusive run. Check relevant code and run again.")

#  Key Export Check
print("Checking if keys were correctly exported!")
log.log("\n\n\nBeginning key export test.")
os.chdir(os.path.join(out,"Non-Inc"))
keysExpected = ["DR.key", "DRPub.key"]
passing = True

for key in keysExpected:
    if os.path.isfile(key):
        with open(key, "r") as k:
            keyIn = gpg.import_keys(k.read())
            if keyIn.count != 1:
                print("Keys imported: %s count, expected 1." % keyIn.count)
                log.log("WARNING: %s failed to import, got %s keys." % (key, keyIn.count))
                passing = False
            else:
                print("%s imported successfully." % key)
if passing:
    print("Keys were exported successfully!")
    log.log("Test passed!")
else:
    print("Some keys did not pass correctly.")
    log.log("Test failed: please confirm you entered the correct passphrase and check the export code!")

# Certificate Check Tests
print("Beginning Networking Tests -- SSL Authentication Checks!")
log.log("\n\n\nBeginning Network Testing Block")
os.chwd(permaHome)
os.system("python3.6 testServerBad.py")
os.system("python3.6 testServerGood.py")


## Test Server Rejection
sslcontext = dev.getSSLContext("test")
sock = dev.establishRemote('localhost', 49152, sslcontext)

if sock == False:
    print("Tapestry correctly rejected testServerBad")
    log.log("HTTPS Failure Test - PASSED")
elif isinstance(sock, http.server.socket): # TODO correct this class
    print("Tapestry incorrectly accepted testServerBad's bad SSL Cert.")
    log.log("HTTPS Failure Test - FAILED")
else:
    print("Tapestry's establishRemote method provided an unexpected return.")
    log.log("HTTPS Failure TEST - FAILED (Unexpected Item In Bagging Area)")

## Test Server Acceptance
sock = dev.establishRemote('localhost', 49153, sslcontext)

if isinstance(sock, http.server.socket):
    print("Tapestry correctly accepted testServerGood")
    log.log("HTTPS Success Test - PASSED")
elif sock == False: # TODO correct this class
    print("Tapestry incorrectly rejected testServerGood")
    log.log("HTTPS Success Test - FAILED")
else:
    print("Tapestry's establishRemote method provided an unexpected return.")
    log.log("HTTPS Success TEST - FAILED (Unexpected Item In Bagging Area)")

## Graceful Failure Test
proceed = dev.checkConnection(False)

if proceed.go == True:
    print("Tapestry will crash if the SSL handshake fails")
    log.log("HTTPS Graceful Failure Test - FAILED")
else:
    print("Tapestry will enter graceful failure mode if SSL handshake fails.")
    log.log("HTTPS Graceful Failure Test - PASSED")

# Metadata Tests
## Output Format Confirmation Test
sampleMDOutput = dev.sendMetadata(True, test=True) # if test, build a default metadata object instead of doing it properly.
controlMDOutput = json.loads('''
{
    "version" : "test",
    "size" : 1337
    "inclusive" : False
    "included" : ["docs", "photos", "testing"]
    "compiled" : "1498-08-17"
    "org" : "Tapestry Development Team"
    "machine" : "TestRig"
    "signatory" : "Borgia, Cesare"
}
''')

for key, value in controlMDOutput:
    try:
        if value == sampleMDOutput[key]:
            print("Metadata Output Testing - %s - PASSED" % key)
            log.log("Metadata Output Testing - %s - PASSED" % key)
        else:
            print("Metadata Output Testing - %s - FAILED" % key)
            log.log("Metadata Output Testing - %s - FAILED" % key)
    except KeyError:
        print("Metadata Output Error - %s Not Found In Test Output" % key)
        log.log("Metadata Output Testing - %s - FAILED: Not Present" % key)

## Reception Comparison Test
sampleMDInput = dev.rxMetadata(True, test=True) # In this configurations sends the metadata request string to testServerGood's port.
controlMDInput = json.loads('''
{
    "version" : "test",
    "size" : 1337
    "inclusive" : False
    "included" : ["docs", "photos", "testing"]
    "compiled" : "1498-08-17"
    "org" : "Tapestry Development Team"
    "machine" : "TestRig"
    "signatory" : "Borgia, Cesare"
}
''')

for key, value in controlMDInput:
    try:
        if value == sampleMDOutput[key]:
            print("Metadata Input Testing - %s - PASSED" % key)
            log.log("Metadata Input Testing - %s - PASSED" % key)
        else:
            print("Metadata Input Testing - %s - FAILED" % key)
            log.log("Metadata Input Testing - %s - FAILED" % key)
    except KeyError:
        print("Error: Key %s not found in observed output" % key)
        log.log("Metadata Input Testing - %s - FAILED: Not Present" % key)

# FTP Tests - Must Run After Corpus Generation
conFTP = dev.switchToFTP(sock) # Switches over to connect to the FTP test server.
if isinstance(conFTP, ftp.FTP()):
    print("FTP Handover Testing - PASSED")
    log.log("FTP Handover Testing - PASSED")
    passFTP = True
else:
    print("FTP Handover Testing - FAILED")
    print("Skipping remaining FTP Tests")
    log.log("FTP Handover Testing - FAILED")
    log.log("Skipping remaining FTP Tests.")
    passFTP = False

if passFTP:
    ## Test Send Function to Server
    fileTest = os.path.join(pathControl, "controlBlock.tap")
    ### Take Checksum of Block to Send
    controlHash = hashlib.md5()
    controlHash.update(open(fileTest, "r").read())
    ### Send the File to "server"
    dev.sendBlock(fileTest)
    testTxHash = hashlib.md5()
    testTxHash.update(open(fileTest.replace("Control", "Test"), "r").read())

    ### Pull the File Back
    testRxHash = hashlib.md5()
    testRxHash.update(dev.getBlock("controlBlock.tap").read())

    ### Compare All 3 Checksums
    if controlHash == testRxHash:
        print("FTP Recieve Test - PASSED")
        log.log("FTP Receive Test - PASSED")
    else:
        print("FTP Receive Test - FAILED")
        log.log("FTP Recieve Test - FAILED")

    if controlHash == testTxHash:
        print("FTP Push Test - PASSED")
        log.log("FTP Push Test - PASSED")
    else:
        print("FTP Push Test - FAILED")
        log.log("FTP Push Test - FAILED")

# Loom-Specific Tests

## Loom SSAT Exchange

certFile = cfg.get("Networking Options", "Certificate Path")
sessionChallenge = b"0xDEADBEEF"
sessionKey = dev.authLoom(certfile, sessionChallenge, testing=True)

## Loom Upload Function Test
fileTest = os.path.join(pathControl, "controlBlock.tap")
controlHash = hashlib.md5()
controlHash.update(open(fileTest, "r").read())

dev.loomUpload(fileTest, sessionKey, 'localhost', 49153)
fileTest = os.path.join(pathControl.replace("Control", "Test"), "recievedUp.tap")
uploadHash = hashlib.md5.update(open(fileTest, "r").read())

if controlHash == uploadHash:
    print("Loom Upload Test - PASSED")
    log.log("Loom Upload Test - PASSED")
else:
    print("Loom Upload Test - FAILED - Mismatched File Recieved")
    log.log("Loom Upload Test - FAILED - Mismatched File Recieved")

## Loom Download Function Test
dev.loomDownload("recievedUp.tap", sessionKey, 'localhost', 49153)
fileTest = os.path.join(pathControl.replace("Control", "Test"), "recievedDown.tap")
downloadHash = hashlib.md5.update(open(fileTest, "r").read())

if controlHash == downloadHash:
    print("Loom Download Test - PASSED")
    log.log("Loom Download Test - PASSED")
else:
    print("Loom Download Test - FAILED - Mismatched File Recieved")
    log.log("Loom Download Test - FAILED - Mismatched File Recieved")

#  Clear Down!
log.save()

print("After passing this confirmation screen, the test result material will be deleted (except the log). If you need to dissect further, leave this session open or delete the items manually yourself.")
carryOn = input("Press any key to continue. > ")
shutil.rmtree(out)
remKey = gpg.delete_keys(cfg.get("Environment Variables", "Expected FP"), secret=True, expect_passphrase=False)
remKey = gpg.delete_keys(cfg.get("Environment Variables", "Expected FP"))