#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Import Modules
import configparser as cp
from datetime import date
import gnupg
import hashlib
import os
import shutil
import subprocess
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
        self.loggerfile.write("Test Host: %s \n" % host)
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
os.chdir(os.getcwd())

cfg = cp.ConfigParser()
cfg.read("tapestry-test.cfg")
out = cfg.get("Environment Variables", "output path")
uid = cfg.get("Environment Variables", "uid")
host = cfg.get("Environment Variables", "compID")
logs = os.path.join(out, "Logs")

shutil.copy("tapestry-test.cfg", "tapestry-test.cfg.bak") # We create a backup of the config to restore to after testing.

cfg.set("Environment Variables", "output path", os.path.join(out, "Non-Inc"))
with open("tapestry-test.cfg", "w") as warp:
    cfg.write(warp)

pathControl = out.replace("Test", "Control")

gpg = gnupg.GPG(gnupghome=str("/home/" + uid + "/.gnupg"))

#  Establish a Logger for Test Output
if not os.path.isdir((logs)):
    os.mkdir(logs)

logname = ("test-%s-%s.log" % (uid, str(date.today())))
log = simpleLogger(logs, logname)


#  Do the bulk runs and context switching to generate the test outputs (make sure to seperate outputs between runs!)
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
docs = cfg.get("Default Locations/Nix", "docs")
cfg.set("Default Locations/Nix", "docs", docs.replace("Control", "Test"))
pics = cfg.get("Default Locations/Nix", "photos")
cfg.set("Default Locations/Nix", "photos", pics.replace("Control", "Test"))
vids = cfg.get("Additional Locations/Nix", "video")
cfg.set("Default Locations/Nix", "video", vids.replace("Control", "Test"))
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

#  Identity Testing -- Hash to Hash
print("\n\nStarting Identity Test")
hashControl = hashlib.md5()
hashTest = hashlib.md5()
counterMismatch = 0
identical = False

for foo, bar, files in os.walk(pathControl):
    for file in files:
        absfile = os.path.join(foo, file)
        testfile = absfile.replace("Control", "Test")
        with open(absfile, "rb") as f:
            hashControl.update(f)
        with open(testfile, "rb") as f:
            hashTest.update(f)

        if hashControl != hashTest:
            print("Mismatch detected!")
            log.log("Mismatch detected with file: %s" % testfile)
            counterMismatch += 1

if counterMismatch == 0:
    identical = True
    print("Identity test passed with no mismatching detected.")
    log.log("Identity test passed with no mismatching detected.")
else:
    identical = False

#  Encryption and Signing Passing
    # Test if Signatures are Valid
print("Beginning Signature Verification.")
log.log("\n\nBeginning of Signature Verification Test.")
failures = 0
for foo, bar, files in os.walk(out):
    for file in files:
        if file.endswith(".tap.sig"):
            with open(file, "rb") as sig:
                verified = gpg.verify_file(sig, file.lstrip(".sig"))
                if verified.trust_level >= verified.TRUST_FULLY:
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
    for foo, bar, files in os.walk(out):
        for file in files:
            if file.endswith(".tap"):
                with open(file, "rb") as k:
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
    # Compare a test pickle to control pickle.
    # Report the diff (pass if no diff)

#  Compression Testing
    # Test that output is smaller than Blocksize

#Inclusive/Exclusive Differentiation Test
    # Test that /inc is bigger than /non-inc

#  Export Check
    # Check for output!

#  Clear Down!
    # Prompt for Confirmation
    # Delete Items
    # Delete Keys