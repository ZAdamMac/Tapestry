#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Imports Block
import configparser as cp
from datetime import date
import hashlib
import os
import shutil
import subprocess
import time


#  Define Classes
class simpleLogger:  # dedicated skip-logging handler for use in buildBlocks
    def __init__(self, landingdir,name):  # starts the skiplogger and tells it it will be writing to landingdir with name
        landingAbs = os.path.join(landingdir, name)
        if not os.path.exists(landingdir):
            os.makedirs(landingdir)
        self.loggerfile = open(landingAbs, "w")  # This will REPLACE the existing logfile with the new one so be careful
        self.loggerfile.write("===============================================================================\nThis is a log of tests run against some version of Tapestry by the \nruntime-tests.py testing utility. The date is indicated in the filename. \nIt should be made clear that these tests do not indicate any sort of warranty \nor guarantee of merchantability.\n\n=======TEST MACHINE SPECS=======\n")
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

permaHome = os.getcwd()

cfg = cp.ConfigParser()
cfg.read("tapestry-test.cfg")
out = cfg.get("Environment Variables", "output path")
uid = cfg.get("Environment Variables", "uid")
host = cfg.get("Environment Variables", "compID")
test_FTP_user = cfg.get("Network Configuration", "username")
logs = os.path.join(permaHome, "Logs")
blockSize = cfg.get("Environment Variables", "blocksize")

shutil.copy("tapestry-test.cfg", "tapestry-test.cfg.bak") # We create a backup of the config to restore to after testing.

pathControl = out.replace("Test", "Control")

#  Establish a Logger for Test Output
if not os.path.isdir((logs)):
    os.mkdir(logs)

logname = ("runtime_test-%s-%s.log" % (uid, str(date.today())))
log = simpleLogger(logs, logname)


#  Do the bulk runs and context switching to generate the test outputs (make sure to seperate outputs between runs!)
log.log("------------------------------[SAMPLE GENERATION]------------------------------")
log.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
hasher = hashlib.sha256()
hasher.update(open("dev.py", "rb").read())
taphash = hasher.hexdigest()
log.log("\n"+str(taphash)+"\n")

cfg.read("tapestry-test.cfg")
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

cfg.read("tapestry-test.cfg")
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

cfg.read("tapestry-test.cfg")
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
log.log("-------------------------------------------------------------------------------")
log.save()
