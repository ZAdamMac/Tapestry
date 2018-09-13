#! /usr/bin/env python3.6
# Tapestry Backup Automation Tool
# Coded in python3 at Patch Savage Labs
# git: ~/ZAdamMac/Patchs-Tapestry
global version; version = 'DevBuild'  # Sets the version to display. "DevBuild" enables some extra debugging not normally accessable

# Importing Modules
import argparse
import bz2
import configparser
import datetime
from datetime import date
import ftplib
import gnupg
import math
import multiprocessing as mp
import os
import os.path
import pickle
import platform
import shutil
import ssl
import sys
import tarfile
import uuid

# Defining Classes
class skipLogger:  # dedicated skip-logging handler for use in buildBlocks
    def __init__(self, landingdir,name):  # starts the skiplogger and tells it it will be writing to landingdir with name
        landingAbs = os.path.join(landingdir, name)
        if not os.path.exists(landingdir):
            os.makedirs(landingdir)
        self.loggerfile = open(landingAbs, "w")  # This will REPLACE the existing logfile with the new one so BE FUCKING CAREFUL
        self.loggerfile.write("The files in the following locations were excluded from the most recent backup. \n")
        self.loggerfile.write("This was due to their filesize exceeding the configured blocksize limit. \n")
        self.loggerfile.write("\n")

    def log(self, foo):  # Formats foo nicely and adds it to the log
        self.loggerfile.write(foo + '\n')

    def save(self):  # saves the file to disk. Once used you have to re-instance the logger
        self.loggerfile.write("\n")
        self.loggerfile.write("\n This backup was run on " + str(date.today()))
        self.loggerfile.flush()
        self.loggerfile.close()


class tapBlock(object):
    def __init__(self, size, label, index):
        self.sizeCur = 0
        self.sizeMax = size
        self.label = label
        self.full = False
        self.contents = {}
        self.index = index #This is the index number used to find the right lock for later

    def add(self, FID, fSize, fPath):  # General function for adding a file to the box. Called during block assembly.
        if (self.sizeMax - self.sizeCur) < smallest:
            self.full = True
            return "full"
        if fSize > (self.sizeMax - self.sizeCur):  # Handling for files larger than will fit in the current block
            return "pass"
        if fSize <= (self.sizeMax - self.sizeCur):  # This file fits
            self.contents.update({FID: fPath})
            self.sizeCur += fSize
            return "stored"

    def pack(self):  # enques the contents of the block for packaging
        os.chdir(ns.drop)
        global tasks
        for file in self.contents:
            ns.sumJobs += 1
            tasks.put(buildTasker(self.label, file, self.contents[file], self.index))


class tapProc(mp.Process):
    def __init__(self, qTask):
        mp.Process.__init__(self)
        self.qTask = qTask
        os.chdir(ns.workDir)

    def run(self):
        proc_name = self.name
        while True:
            next_task = self.qTask.get()
            if next_task is None:
                debugPrint('%s: Exiting' % proc_name)
                self.qTask.task_done()
                break
            next_task()
            self.qTask.task_done()
        return


class buildTasker(object):
    def __init__(self, tarf, FID, PATH, index):
        self.tarf = tarf
        self.a = FID
        self.b = PATH
        self.index = index #index number of the appropriate mutex

    def __call__(self):
        statusPrint()
        os.chdir(ns.workDir)
        if os.path.exists(self.tarf): #we need to know if we're starting a new file or not.
            fLock = locks[self.index] #Aquires the lock indicated in the index value from the master
            fLock.acquire()
            tar = tarfile.open(name=self.tarf, mode="a:")
            tar.add(self.b, arcname=self.a, recursive=False)
            tar.close()
            fLock.release()
            ns.jobsDone += 1
            statusPrint()

class comTasker(object):
    def __init__(self, t, lvl):
        self.tarf = t
        self.level = lvl

    def __call__(self):
        statusPrint()
        os.chdir(ns.workDir)
        with open(self.tarf, "rb") as b:
            bz2d = self.tarf+".bz2"
            bz2f = bz2.BZ2File(bz2d, "wb", compresslevel=ns.compressLevel)
            shutil.copyfileobj(b, bz2f)
            ns.jobsDone += 1
            statusPrint()
        pass

class encTasker(object):
    def __init__(self, t, fp):
        self.tarf = t
        self.fp = fp

    def __call__(self):
        with open(self.tarf, "r") as p:
            statusPrint()
            os.chdir(ns.workDir)
            tstring = self.tarf
            if not ns.compress:
                tapped = self.tarf.replace(".tar", ".tap")
            else:
                tapped = self.tarf.replace(".tar.bz2", ".tap")
            tgtOutput = os.path.join(ns.drop, tapped)
            debugPrint("Encrypting - sending block to: " + tgtOutput)
            with open(tstring, "rb") as tgt:
                k = gpg.encrypt_file(tgt, self.fp, output=tgtOutput, armor=True, always_trust=True)
            if k.ok:
                debugPrint("Encryption Success.")
            elif not k.ok:
                debugPrint(str(k.status)) #Displays the specific encryption error encountered if encryption fails
            ns.jobsDone += 1
            statusPrint()


class sigTasker(object):
    def __init__(self, block, sigfp):
        self.block = block
        self.fp = sigfp

    def __call__(self):
        statusPrint()
        os.chdir(ns.drop)
        with open(self.block, "rb") as p:
            statusPrint()
            tgtOutput = self.block + ".sig"
            debugPrint("Signing: " + tgtOutput)
            sis = gpg.sign_file(p, keyid=self.fp, output=tgtOutput, detach=True)
            if sis.status != 'signature created':
                print("[Error] Something went wrong in signing %s." % self.block)
            ns.jobsDone += 1
            statusPrint()


class recTask(object): #todo exception handles
    def __init__(self, tar, fid, catdir, pathend):
        self.tar = tar
        self.fid = fid
        self.catdir = catdir
        self.pathend = pathend

    def __call__(self):
        statusPrint()
        absTar = os.path.join(ns.workDir, self.tar)
        pathEnd = self.pathend.strip('~/')
        absFile = os.path.join(self.catdir,pathEnd)
        placement, nameProper = os.path.split(absFile)  # split the pathend component into the subpath from the category dir, and the original filename.
        with tarfile.open(absTar, "r") as tf:
            tf.extract(self.fid, path=placement)  # the file is now located where it needs to be.
        placed = os.path.join(placement, self.fid)
        os.rename(placed, absFile)  # and now it's named correctly.
        debugPrint("Placed " + str(pathEnd))
        ns.jobsDone += 1

class recProc(mp.Process):
    def __init__(self, qTask):
        mp.Process.__init__(self)
        self.qTask = qTask
        os.chdir(ns.drop)

    def run(self):
        proc_name = self.name
        while True:
            next_task = self.qTask.get()
            if next_task is None:
                # Poison pill means shutdown
                debugPrint('%s: Exiting' % proc_name)
                self.qTask.task_done()
                break
            next_task()
            self.qTask.task_done()
        return


# Defining all functions!
def debugPrint(foo):
    if ns.debug:
        print(str(foo))

def statusPrint(): # Prettyprinter of status to keep the system busy.
    global ns
    lengthBar = 15.0
    doneBar = int(round((ns.jobsDone/ns.sumJobs)*lengthBar))
    doneBarPrint = str("#"*int(doneBar)+"-"*int(round((lengthBar-doneBar))))
    percent = int(round((ns.jobsDone/ns.sumJobs)*100))
    text = ("\r{0}: [{1}] {2}%" .format(ns.task, doneBarPrint, percent))
    sys.stdout.write(text)
    sys.stdout.flush()

def announce():
    if __name__ == '__main__':
        print("Welcome to Tapestry Backup Tool Version " + version)
    if platform.system() == "Windows":
        print("Unfortunately, windows functionality is currently due to flaws in the current program structure.")
        print("Please watch the repo for news and updates about this feature.")
        exit()

def init():
    print("Configuration file not found.")
    print("Please obtain a new copy of tapestry.cfg from the repo, or ensure that your copy is stored in the same directory as the tapestry script file you are running.")
    exit()

def genKey():
    print("You have indicated you wish to have Tapestry generate a new Disaster Recovery Key.")
    print(("This key will be a %s -bit RSA Key Pair with the credentials you specify." % ns.keysize))
    print("This key will not expire by default. If you need this functionality, add it in GPG.")
    nameKey = str(input("User/Organization Name: "))
    contactKey = str(input("Recovery Contact Email: "))
    print("You will be prompted externally to enter a passphrase for this key via your default pinentry program.")
    inp = gpg.gen_key_input(key_type="RSA", key_length=ns.keysize, name_real=nameKey, name_comment="Tapestry Recovery",
                            name_email=contactKey)
    keypair = gpg.gen_key(inp)
    fp = keypair.fingerprint  # Changes the value of FP to the new key
    config.set("Environment Variables", "Expected FP", str(fp))  # sets this value in config
    ns.activeFP = keypair.fingerprint
    with open(cfg, "w") as cf:
        config.write(cf)
    if not os.path.isdir(ns.drop):
        os.mkdir(ns.drop)
    os.chdir(ns.drop)
    pubOut = gpg.export_keys(fp)
    pubFile = os.open("DRPub.key", os.O_CREAT | os.O_RDWR)
    pubHandle = os.fdopen(pubFile, "w")
    pubHandle.write(str(pubOut))
    pubHandle.close()
    try:
        keyOut = gpg.export_keys(fp, True, expect_passphrase=False)
        keyFile = os.open("DR.key", os.O_CREAT | os.O_RDWR)
        keyHandle = os.fdopen(keyFile, "w")
        keyHandle.write(str(keyOut))
        keyHandle.close()
    except ValueError: # Most Probable cause for this is that the version of the gnupg module is outdated, so we need our alternate handler.
        print("An error has occured which has prevented the private side of the disaster recovery key from being exported.")
        print("This error is likely caused by this system's version of the python-gnupg module being outdated.")
        print("You can export the key manually using the method of your choice.")

    print("The exported keys have been saved in the output folder. Please move them to removable media or other backup.")


def loadKey():
    if ns.genKey:
        genKey()
    ns.activeFP = config.get("Environment Variables", "Expected FP")
    keys = gpg.list_keys(keys=ns.activeFP)
    try:
        location = keys.key_map[ns.activeFP] # If the key is in the dictionary, hooray!
        found = True
    except KeyError:
        found = False
    if found is False:
        print('''"Unable to locate the key with fingerprint "%s"''' % ns.activeFP)
        print("This could be due to either a configuration error, or the key needs to be re-imported.")
        print("Please double-check your configuration and keyring and try again.")
        cleardown()
        exit()
    debugPrint("Fetching key %s from Keyring" % ns.activeFP)
    debugPrint(ns.activeFP)


def createDIRS():
    if not os.path.exists(ns.workDir):
        os.mkdir(ns.workDir)
    if not os.path.exists(ns.drop):
        os.mkdir(ns.drop)

def findblock():  # Time to go grepping for taps!
    os.chdir(ns.media)
    global foundBlocks; foundBlocks = []
    for foo, bar, files in os.walk(ns.media):
        for file in files:
            if file.endswith(".tap"):
                os.chdir(foo)
                foundBlocks.append(file)


def validateBlock():
    print("Checking the validity of this tapfile's signature.")
    global valid
    global sig; sig = None
    for dont, care, files in os.walk(ns.media):
        for file in files:
            debugPrint("Looking for a sig at file: " + file)
            if file.endswith(".sig"):
                sig = os.path.join(dont, file)
            elif file.endswith(".tap"):
                data = os.path.join(dont, file)
            else:
                continue
    if sig is None:
        print("No signature is available for this block. Continue?")
        go = input("y/n?")
        if go.lower() == "y":
            valid = True
        else:
            print("Aborting backup.")
            cleardown()
            exit()
    else:
        with open(sig, "rb") as fsig:
            verified = gpg.verify_file(fsig, data)
        if verified.trust_level is not None and verified.trust_level >= verified.TRUST_FULLY:
            valid = True
            print("This block has been verified by %s, which is sufficiently trusted." % verified.username)
        else:
            print("This block claims to have been signed by %s." % verified.username)
            print("The signature's trust level is %s. Continue?" % verified.trust_text)
            go = input("y/n?")
            if go.lower() == "y":
                valid = True
            else:
                print("Aborting backup.")
                cleardown()
                exit()


def decryptBlock():
    global foundBlocks
    for block in foundBlocks:
        outputTGT = str(os.path.join(ns.workDir, block))
        with open(block, "rb") as kfile:
            baz = gpg.decrypt_file(kfile, output=outputTGT, always_trust=True)
            if not baz.ok: # Weird Include to actually force the system to finish computing the value of baz without waiting for debugprint to do its job.
                pass
            with open(outputTGT, "rb") as dropped:
                signature = dropped.read(3)
                if signature.startswith(b"BZh"):
                    # we need to add some code here to swap the file we just spat out with a decompressed version.
                    shutil.copy(outputTGT, (outputTGT+".temp"))
                    with bz2.BZ2File(outputTGT+".temp", "rb") as compressed:
                        with open(outputTGT, "wb") as uncompressed:
                            shutil.copyfileobj(compressed, uncompressed)
                    pass
            if not baz.ok:
                debugPrint("Decryption Error: " + str(baz.status))
                print("A decryption error was encountered. Tapestry will now shut down.")
                cleardown()
                exit()

def openPickle():
    for foo, bar, files in os.walk(ns.workDir):
        for file in files:
            if file.endswith(".tap"):
                with tarfile.open(os.path.join(foo, file), "r") as tfile:
                    tfile.extract("recovery-pkl", path=ns.workDir)
                    break
        break

    for a, b, files in os.walk(ns.workDir):
        for file in files:
            if file == "recovery-pkl":
                foo = os.path.join(a, file)
                global recPaths
                global recSections
                global numBlocks
                with open(foo, "rb") as baz:
                    listRecovery = pickle.load(baz)
                numBlocks, recPaths, recSections = listRecovery
    if len(
            recPaths) > 0:  # Throws an internal error if the required files are not properly mounted and closes the program so that it will not damage the archive
        print("Found Recovery Table 1")
    else:
        print(
            "There was a problem finding the file 'recovery-pkl' on the disk. Please reload this program and try again.")
        cleardown()  # Deletes temporary files to prevent system bloat
        exit()
    if len(recSections) > 0:
        print("Found Recovery Table 2")
    else:
        print(
            "There was a problem finding the file 'recovery-pkl' on the disk. Please reload this program and try again.")
        cleardown()
        exit()

def unpackBlocks():
    if __name__ == '__main__':
        global tasker
        tasker = mp.JoinableQueue()
        ns.task = "Unpacking Files"
        ns.jobsDone = 0
        ns.sumJobs = 0
        for foo, bar, files in os.walk(ns.workDir):
            for file in files:
                if file.endswith(".tap"):
                    with tarfile.open(os.path.join(foo, file), "r")as tf:
                        for item in tf.getnames():  # at this point item yields a tap FID
                            if item == "recovery-pkl": #avoids a keyerror later.
                                continue
                            cat = recSections[item]
                            try:
                                catdir = dirActual[cat]
                            except KeyError:
                                catdir = os.path.join(ns.drop, cat)
                            finally:
                                if not os.path.isdir(catdir):
                                    os.mkdir(catdir)
                            pathend = recPaths[item]
                            ns.sumJobs += 1
                            tasker.put(recTask(file, item, catdir, pathend))

        global workers; workers = []
        for i in range(ns.numConsumers):
            workers.append(recProc(tasker))
        for w in workers:
            w.start()
        tasker.join()
        for foo in range(ns.numConsumers):
            tasker.put(None)  # seed poison pills at the end of the queue to kill the damn consumers
        tasker.join()


def cleardown():
    if os.path.exists(ns.workDir):
        shutil.rmtree(ns.workDir)
        global gpg; gpg = None


def getContents(category, tgt):
    print("Currently walking the " + category + " directory.")
    for fromRoot, dirs, files, in os.walk(str(tgt)):
        for item in files:
            global sumSize
            global counterFID
            global listSection
            node = uuid.getnode()
            counterFID = uuid.uuid1(node=node)
            metaTGT = os.path.join(fromRoot, item)
            size = os.path.getsize(metaTGT)
            fooSize = sumSize + size
            sumSize = fooSize
            listAbsolutePaths.update({str(counterFID): str(metaTGT)})
            listFSNames.update({str(counterFID): str(item)})
            listSizes.update({str(counterFID): str(size)})
            relativePath = metaTGT.replace(tgt, "~",
                                           1)  # removes tgt from the path string, leaving the path string after the root of TGT, including subfolders, for recovery.
            listRelativePaths.update({str(counterFID): str(relativePath)})
            listSection.update({str(counterFID): str(category)})
    debugPrint("After crawling " + category + " there are " + str(len(listAbsolutePaths)) + " items in the index.")

def makeIndex():  # does some operations to the working dictionaries to remove items that are too large and place them in order.
    print("Compiling the working indexes")
    global workIndex
    workIndex = sorted(listSizes, key=listSizes.__getitem__)
    workIndex.reverse()  # yields the index sorted by descending file size.
    for item in workIndex:  # We need to remove the largest items.
        size = int(listSizes[item])
        if size > blockSizeActual:
            global sumSize; sumSize = sumSize - size  # In retrospect this was obviously needed for blockbuild to work right later.
            print("Error: %s is too large to be processed and will be excluded." % listFSNames[item])
            skiplogger.log(listAbsolutePaths[item])
            del workIndex[int(item)]
    global smallest
    smallest = int(listSizes[workIndex[(len(workIndex)-1)]])
    print("The working index contains %s files." % len(workIndex))

def buildBlocks():
    global blocks
    blocks = []
    print("Beginning the blockbuilding process. This may take a moment.")
    numBlocks = math.ceil(sumSize / blockSizeActual)
    debugPrint("numblocks = "+ str(numBlocks))
    for i in range(int(numBlocks)):
        SID = str(str(compid) +"-"+ str(date.today())+"-"+ str(i+1) + ".tar")
        blocks.append(tapBlock(blockSizeActual, SID, i))
    for block in blocks:
        debugPrint("Testing in Block: " + str(block))
        activeIndex = workIndex.copy() #At the start of each block we clone the whole index for it to track over.
        if not block.full:
            for FID in activeIndex:
                pos = workIndex.index(FID)
                fSize = listSizes[FID]
                status = block.add(FID, int(fSize), listAbsolutePaths[FID])
                if status == "pass":
                    pass
                elif status == "stored":
                    del workIndex[pos] #placed items are removed from the work index
        if len(workIndex) == 0:
            break
    print("There are no items left to sort.")
    placePickle()

def placePickle():  # generates the recovery pickle and leaves it where it can be found later.
    if __name__ == "__main__":
        os.chdir(ns.workDir)
        global sumBlocks
        sumBlocks = len(blocks)
        listRecovery = [sumBlocks, listRelativePaths,
                        listSection]  # Believe it or not, this number and these two lists are all we need to recover from a tapestry backup!
        recPickle = os.open("recovery.pkl", os.O_CREAT | os.O_RDWR)
        filePickles = os.fdopen(recPickle, "wb")
        pickle.dump(listRecovery, filePickles)
        filePickles.close()
        pathPickle = os.path.join(ns.workDir, "recovery.pkl")
        for block in blocks:
            tar = tarfile.open(block.label, "w:") #attempting workaround to append issue.
            tar.add(pathPickle, arcname="recovery-pkl", recursive=False)
            tar.close()

def processBlocks():  # signblocks is in here now
    print("Packaging Blocks.")
    debugPrint("Spawning %s processes." % ns.numConsumers)
    if __name__ == '__main__':
        global blocks
        os.chdir(ns.workDir)
        global tasks
        tasks = mp.JoinableQueue()
        consumers = []
        global locks
        locks = []
        for i in range(ns.numConsumers):
            consumers.append(tapProc(tasks))
        ns.task = "Tarfile Generation"
        ns.jobsDone = 0
        ns.sumJobs = 0
        for b in blocks:
            b.pack()
            locks.append(master.Lock())
        for w in consumers:
            w.start()
        tasks.join()
        print("\nPacked Blocks")
        ns.task = "Compression"
        ns.jobsDone = 0
        if ns.compress: # Compression structured differently to force only MAIN to do it.
            compressionQueue = []
            for foo, bar, tars in os.walk(ns.workDir):
                for tar in tars:
                    if tar.endswith(".tar"):
                        compressionQueue.append(comTasker(tar, ns.compressLevel))
        print("\nCompression Enqueued")
        ns.sumJobs = len(compressionQueue)
        for foo in compressionQueue:
            foo()

        ns.task = "Encryption"
        ns.jobsDone = 0
        ns.sumJobs = 0
        for foo, bar, files in os.walk(ns.workDir):
            if not ns.compress:
                suffix = ".tar"
            else:
                suffix = ".bz2"
            for file in files:
                if file.endswith(suffix):
                    ns.sumJobs += 1
                    tasks.put(encTasker(file, ns.activeFP))
        print("\nEncryption enqueued")
        tasks.join()
        ns.task = "Signing"
        ns.jobsDone = 0
        ns.sumJobs = 0
        if ns.signing:
            for foo, bar, taps in os.walk(ns.drop):
                for tap in taps:
                    if tap.endswith(".tap"):
                        ns.sumJobs += 1
                        tasks.put(sigTasker(tap, ns.sigFP))
        print("\nSigning Enqueued")
        for w in consumers: #Finally, poison pill the worker processes to terminate them.
            tasks.put(None)
        tasks.join()
        debugPrint("End of processBlocks()")


def buildMaster():  # summons the master process and builds its corresponding namespace, then assigns some starting values
    if __name__ == "__main__":
        global master
        master = mp.Manager()
        global ns
        ns = master.Namespace()

        ns.currentOS = platform.system()  # replaces old global var currentOS
        ns.date = datetime.date
        ns.home = os.getcwd()
        ns.secret = None  # Placeholder so that we can use this value later as needed. Needs to explicitly be none in case no password is used.

def parseArgs():  # mounts argparser, crawls it and then assigns to the managed namespace
    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="Automatically backup or restore personal files from the system. \n Full documentation at https://github.com/ZAdamMac/Tapestry/blob/master/DOCUMENTATION.md")
        parser.add_argument('--rcv', help="Recover a previous archive from disk.", action="store_true")
        parser.add_argument('--inc', help="Tells the system to include non-default sections in the backup process.",
                            action="store_true")
        parser.add_argument('--debug', help="Increase output verbosity.", action="store_true")
        parser.add_argument('--genKey', help="Generates a new key before proceeding with any other functions called.",
                            action="store_true")
        args = parser.parse_args()

        ns.rcv = args.rcv
        ns.inc = args.inc
        ns.debug = args.debug
        ns.genKey = args.genKey

def parseConfig():  # mounts the configparser instance, grabs the config file, and passes its values into the namespace
    if __name__ == "__main__":
        global config
        config = configparser.ConfigParser()
        global cfg
        if version == "DevBuild":
            cfg = "tapestry-test.cfg"
        else:
            cfg = "tapestry.cfg"

        if os.path.exists(os.getcwd() + "/" + cfg):
            config.read(cfg)
            global uninit
            uninit = False

        ns.expectedFP = config.get("Environment Variables", "Expected FP")
        ns.fp = config.get("Environment Variables", "Expected FP")  # Can be changed during the finding process.
        ns.signing = config.getboolean("Environment Variables", "Sign by Default")
        ns.sigFP = config.get("Environment Variables", "Signing FP")
        ns.keysize = config.getint("Environment Variables", "keysize")
        ns.compress = config.getboolean("Environment Variables", "Use Compression")
        ns.compressLevel = config.getint("Environment Variables", "Compression Level")
        ns.step = "none"
        ns.sumJobs = 0
        ns.jobsDone = 0
        ns.modeNetwork = config.get("Network Configuration", "mode")
        ns.addrNet = config.get("Network Configuration", "server")
        ns.portNet = config.getint("Network Configuration", "port")
        ns.nameNet = config.get("Network Configuration", "username")
        ns.nameNet = config.get("Network Configuration", "remote drop location")
        ns.retainLocal = config.getboolean("Network Configuration", "Keep Local Copies")

        # We also declare some globals here. They aren't used in the children so they aren't part of ns, but they still need to be declared and still come from config.
        global blockSizeActual
        blockSizeActual = config.getint("Environment Variables", "blockSize") * (
        2 ** 20)  # cfg asks the user for MB, but for actual processes we need bytes
        global compid; compid = config.get("Environment Variables", "compid")
        global driveletter
        driveletter = config.get("Environment Variables",
                                 "recovery path")  #path to the removable disk mount point. Used mostly for testing.
        global uid
        uid = config.get("Environment Variables", "uid")  # Not sure actually used anywhere!

    if ns.currentOS == "Linux":
        ns.workDir = "/tmp/Tapestry/"
        ns.desktop = str("/home/" + uid + "/Desktop")
        ns.gpgDir = str("/home/" + uid + "/.gnupg")
        ns.media = driveletter
    elif ns.currentOS == "Windows":
        ns.workDir = "C:/Windows/Temp"
        ns.desktop = str("C:/Users/" + uid + "/Desktop")
        ns.gpgDir = "C:/Program Files (x86)/GNU/GnuPG"
        ns.media = driveletter
    ns.drop = config.get("Environment Variables", "Output Path")
    ns.numConsumers = calcConsumers()
    debugPrint("I am operating with %s consumers." % ns.numConsumers)

def startLogger():
    global skiplogger
    skiplogger = skipLogger(ns.drop, "Skipped Files")

def startGPG():
    global gpg
    gpg = gnupg.GPG(gnupghome=ns.gpgDir, verbose=ns.debug)

def buildOpsList():
    global listDefaults
    global listAdditionals
    global dirActual

    if ns.currentOS == "Linux":
        listDefaults = dict(config.items("Default Locations/Nix"))
        listAdditionals = dict(config.items("Additional Locations/Nix"))
    if ns.currentOS == "Windows":
        listDefaults = dict(config.items("Default Locations/Win"))
        listAdditionals = dict(config.items("Additional Locations/Win"))

    global listRun

    if ns.inc:
        listRun = listDefaults.copy()
        listRun.update(listAdditionals)
    else:
        listRun = listDefaults

    dirActual = listDefaults.copy()
    dirActual.update(listAdditionals)

    ns.dirActual = dirActual #This last value needs to go to namespace because it is needed by the worker processes too.

def calcConsumers(): #  Simple function, returns an appropriate number of consumers based on available RAM and available processor cores.
    cielCores = os.cpu_count()
    return cielCores

def getSSLContext(test=False):  # Construct and return an appropriately-configured SSL Context object.
    tlsContext = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    tlsContext.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
    if ns.modeNetwork.lower() == "loom":
        tlsContext.load_cert_chain(ns.clientCert)
    if test:
        tlsContext.load_verify_locations(cafile="testcert.pem")
    return tlsContext

def connectFTP(url, port, ssl_context, username, password):  # Establish and return a valid FTP connection object.
    if username is not None:
        if password is None:
            password = ""
    elif username is None:
        username = ''
    if port is None:
        tgt = url
    else:
        tgt = url + ":" + str(port)
    if ssl_context is None:
        link = ftplib.FTP(host=tgt, user=username, passwd=password)
    else:
        link = ftplib.FTP_TLS(host=tgt, user=username, passwd=password, context=ssl_context)
    if username != '':
        link.login()
    return link

def sendFile(ftp_link, upload): # locate file at string "target" and send over FTP_link
    ftp_link.storbinary("STOR %s" % upload, open(upload, "rb"))

def grepBlocks(label, date, ftp_connect):  # fetch the list of blocks from Label on Date.
    index = ftp_connect.nlst()
    lead = ( "%s-%s" % (label, date))
    listFetch = []
    for file in index:
        if file.startswith(lead):
            listFetch.append(file)
    return len(listFetch), listFetch

def fetchBlock(fname, ftp_connect, dirDestination): # fetch fname from the server
    with open(os.path.join(dirDestination, fname), "wb") as fo:
        ftp_connect.retrbinary(fname, fo)


#We're gonna need some globals
global counterFID; counterFID = 0
global sumSize; sumSize = 0
global listAbsolutePaths; listAbsolutePaths = {}
global listRelativePaths; listRelativePaths = {}
global listSizes; listSizes = {}
global listFSNames; listFSNames = {}
global listSection; listSection = {}

# Runtime
if __name__ == "__main__":
    global compid
    announce()
    buildMaster()
    parseArgs()
    parseConfig()
    startLogger()
    startGPG()
    if uninit:
        init()
        exit()
    elif ns.rcv:
        if ns.modeNetwork.lower() == "ftp":
            input("Tapestry is presently configured to an FTP drop. Please ensure you have a connection, and press any key to continue.")
            useDefaultCompID = input("Would you like to recover files for %s? (y/n)>" % compid).lower()
            if useDefaultCompID == "n":
                print("Please enter the name of the computer you wish to recover files for:")
                compid = input("Case Sensitive: ")
            print("Please enter the date for which you wish to recover files:")
            tgtDate = input("YYYY-MM-DD")
            pw = input("Enter the FTP password now (if required)") # TODO add password masking to both these functions.
            ftp_link = connectFTP(ns.addrNet, ns.portNet, getSSLContext(), ns.nameNet, pw)
            countBlocks, listBlocks = grepBlocks(compid, tgtDate, ftp_link)# TODO add a test for this function.
            if countBlocks == 0:
                print("No blocks for that date were found - check your records and try again.")
                ftp_link.quit()
                exit()
            else:
                ns.media = ns.workDir
                for block in listBlocks:
                    fetchBlock(block, ftp_link, ns.media)
                ftp_link.quit()
        usedBlocks = []
        loadKey()
        buildOpsList()
        createDIRS()
        findblock()
        validateBlock()
        decryptBlock()
        openPickle()
        print("This backup exists in %d blocks." % numBlocks)
        for foo, bar, found in os.walk(ns.workDir):
            countBlocks = len(found)-1
        print("So far, you have supplied %d blocks." % countBlocks)
        while countBlocks < numBlocks:
            input("Please insert the next disk and press enter to continue.")
            findblock()
            validateBlock()
            decryptBlock()
        unpackBlocks()
        print("Any files with uncertain placement were moved to the output folder.")
        print("All blocks have now been unpacked. Tapestery will clean up and exit.")
        cleardown()
        exit()
    else:
        createDIRS()
        buildOpsList()
        print("Tapestry is configuring itself. Please wait.")
        loadKey()
        print("Tapestry is preparing the backup index. This may take a few moments.")
        for category in listRun:
            getContents(category, listRun[category])
        makeIndex()
        buildBlocks()
        processBlocks()
        if ns.modeNetwork.lower() == "none":
            print("\nThe processing has completed. Your .tap files are here:")
            print(str(ns.drop))
            print("Please archive these expediently.")
            cleardown()
            exit()
        elif ns.modeNetwork.lower() == "ftp":
            print("\nTapestry has been configured to use an FTP drop for file output.")
            print("The program will now connect to %s as user %s and place the files in %s" % (ns.addrNet, ns.nameNet, ns.netDrop))
            pw = input("Enter the FTP password now (if required): ")
            instFTP = connectFTP(ns.addrNet, ns.portNet, getSSLContext(test=False), ns.nameNet, pw)
            for foo, bar, files in os.walk(ns.drop):
                for file in files:
                    if file.endswith(".tap") or file.endswith(".sig"):
                        sendFile(instFTP, file)
            instFTP.quit()
            print("All files have been successfully uploaded to the FTP except as indicated.")
        if ns.retainLocal:
            print("Your files are also being retained locally, and are here:")
            print(str(ns.drop))
            cleardown()
            exit()
        else:
            print("Your network configuration is set such that files have not been retained locally.")
            for foo, bar, files in os.walk(ns.drop):
                for file in files:
                    if file.lower() != "skipped files":
                        os.chdir(ns.drop)
                        os.remove(file)
            print("The redundant files have been removed - Tapestry will now close.")
            cleardown()
            exit()