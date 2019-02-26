#  Functional Testing Script for Tapestry versions 1.0 and later
#  For full commentary and documentation view TESTDOCS.md in the repo.

#  Imports Block
import configparser as cp
from datetime import date
import hashlib
import os
import shutil
import subprocess
from Development.Testing.tests import framework
import time


def runtime():
    perma_home = os.getcwd()

    cfg = cp.ConfigParser()
    cfg.read("tapestry-test.cfg")
    out = cfg.get("Environment Variables", "output path")
    uid = cfg.get("Environment Variables", "uid")
    host = cfg.get("Environment Variables", "compID")
    test_ftp_user = cfg.get("Network Configuration", "username")
    logs = os.path.join(perma_home, "Logs")
    block_size = cfg.get("Environment Variables", "blocksize")
    dev_level, bar = os.path.split(perma_home)
    path_to_tapestry = os.path.join("Source", "Tapestry")
    path_to_tapestry = os.path.join(path_to_tapestry, "tapestry.py")
    full_path_tapestry = os.path.join(dev_level, path_to_tapestry)

    shutil.copy("tapestry-test.cfg", "tapestry-test.cfg.bak")

    path_control = out.replace("Test", "Control")

    #  Establish a Logger for Test Output
    if not os.path.isdir(logs):
        os.mkdir(logs)

    logname = ("runtime_test-%s-%s.log" % (uid, str(date.today())))
    log = framework.SimpleLogger(logs, logname, "runtime-tests")

    # Do the bulk runs and context switching to generate the test outputs
    # (make sure to seperate outputs between runs!)
    log.log("------------------------------[SAMPLE GENERATION]------------------------------")
    log.log("\nThis log is for a test of a development version of Tapestry, with SHA256 hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/Tapestry/tapestry.py", "rb").read())
    taphash = hasher.hexdigest()
    log.log("\n"+str(taphash)+"\n")
    log.log("\nWhich relies on the classes library with hash:")
    hasher = hashlib.sha256()
    hasher.update(open("../Source/Tapestry/classes.py", "rb").read())
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
    waiting = subprocess.run("python3.6", "dev.py", ("--genKey", "--devtest"))
    elapse = framework.elapsed(start)
    print("--genKey completed in %s" % elapse)
    log.log("Key Generation Mode Test Completed in %s - Returned:" % elapse)
    log.log(str(waiting))

    cfg.read("tapestry-test.cfg")
    cfg.set("Environment Variables", "output path", os.path.join(out, "Inc"))
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)

    print("Now beginning --inc test.")
    start = time.monotonic()
    waiting = subprocess.run("python3.6", "dev.py", ("--inc", "--devtest"))
    elapse = framework.elapsed(start)
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
    cfg.remove_option("Additional Locations/Nix", "Music")
    # This should still wind up in corpus if you didn't break directionless recovery.
    with open("tapestry-test.cfg", "w") as warp:
        cfg.write(warp)

    print("Now beginning --rcv test.")
    start = time.monotonic()
    waiting = subprocess.run("python3.6", "dev.py", ("--rcv", "--devtest"))
    elapse = framework.elapsed(start)
    print("--rcv completed in %s" % elapse)
    log.log("Recovery Mode Test Completed in %s - Returned:" % elapse)
    log.log("%s" % waiting)

    shutil.copy("tapestry-test.cfg.bak", "tapestry-test.cfg")
    print("Sample generation complete!")
    log.log("-------------------------------------------------------------------------------")
    log.save()

if __name__ == "__main__":
    runtime()
