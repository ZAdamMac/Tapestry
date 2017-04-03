#PatchTapestry Bespoke Backup Tool
#Written for Python 2.7.12

#Importing Modules
import argparse
import bz2
import ConfigParser
import datetime
import getpass
import gnupg
import math
import operator
import os
import os.path
import pickle
import platform
import shutil
import sys
import tarfile


#Setting up ConfigParser
global uninit
config = ConfigParser.SafeConfigParser()
if os.path.exists(os.getcwd()+"/tapestry.cfg"):
	config.read("tapestry.cfg")
	uninit = False
else: #the finished version should include a tapestry.cfg file by default for clarity
	uninit = True
	config.add_section("Environment Variables")
	config.add_section("Default Locations/Nix")
	config.add_section("Additional Locations/Nix")
	config.add_section("Default Locations/Win")
	config.add_section("Additional Locations/Win")
	config.set("Environment Variables", "blockSize", "4000")
	config.set("Environment Variables", "expected fp", "0")
	config.set("Environment Variables", "compid", "uninit")
	config.set("Environment Variables", "uid", "uninit") #as a portable function this should work in both Linux and Windows
	if platform.system() == "Linux": #Some defaults could be better
		uname = os.uname()
		config.set("Environment Variables", "compid", str(uname[1])) #gets the nodeid and sets it as the computer's name.
	configFile = os.open("tapestry.cfg", os.O_CREAT|os.O_RDWR)
	os.close(configFile)
	with open("tapestry.cfg", "r+") as t:
		config.write(t)
			
	
#Setting up argparse
parser = argparse.ArgumentParser(description="Automatically backup or restore personal files from the system.")
parser.add_argument('--rcv', help="Recover a previous archive from disk.", action="store_true")
parser.add_argument('--setup', help="Loads the program in user configuration mode", action="store_true")
parser.add_argument('--inc', help="Tells the system to include non-default sections in the backup process.", action="store_true")
parser.add_argument('--debug', help="Increase output verbosity.", action="store_true")
args = parser.parse_args()

#Initializing Nonconfig Global Vars
global blockSizeActual; blockSizeActual = config.getint("Environment Variables", "blockSize") * (2**20) #The config file defines blockSize in MB, this gives bytes
global plainOutput
version = "0.2.0"
global currentOS; currentOS = platform.system()
foundKey = False
listFSNames = {}
listSizes = {}
listRelativePaths = {}
listSection = {}
listAbsolutePaths = {}
global homeDir; homeDir = os.getcwd()
global sumSize; sumSize = 0
global counterFID; counterFID = 0
global uid; uid = config.get("Environment Variables", "uid")
global compid; compid = config.get("Environment Variables", "compid")
global desktop #this is probably the clumsy way.
if currentOS == "Linux":
	desktop = str("/home/"+uid+"/Desktop")
elif currentOS == "Windows":
	desktop = str("C:/Users/"+uid+"/Desktop")
global gpgDir #Currently Dumb
if currentOS == "Linux":
	gpgDir = str("/home/"+uid+"/.gnupg")
elif currentOS == "Windows":
	gpgDir = "dummytest" #TODO you know what to do
global fp; fp = config.get("Environment Variables", "Expected FP")
	
#Initializing Python-GnuPG
if not uninit:
	gpg = gnupg.GPG(gnupghome=gpgDir)
	
#Populating controller lists
global listDefaults
global listAdditionals
global dirActual 

if currentOS == "Linux":
	listDefaults = dict(config.items("Default Locations/Nix"))
	listAdditionals = dict(config.items("Additional Locations/Nix"))
if currentOS == "Windows":
	listDefaults = dict(config.items("Default Locations/Win"))
	listAdditionals = dict(config.items("Additional Locations/Win"))

global listRun

if args.inc:
	listRun = listDefaults.copy()
	listRun.update(listAdditionals)
else:
	listRun = listDefaults

dirActual = listDefaults.copy() #Replaces the old diractual calls from pre-0.2 without destroying function
dirActual.update(listAdditionals)
	
#Defining Functions
def findKeyfile(arg): #mounts indicated key "pub" or "sec" from removable media with automagic.
	if arg == "pub":
		tgt = "DRPub.key"
	elif arg == "sec":
		tgt = "DR.key"
	if currentOS == "Linux":
		dirSearch = ("/media/"+uid)
		debugPrint(dirSearch)
		for root, dirs, files in os.walk(dirSearch):
			for file in files:
				if file == tgt:
					global foundKey
					foundKey = True
					global pathKey
					pathKey = os.path.join(root, tgt)
					debugPrint("Found key at: "+pathKey)
	if currentOS == "Windows":
		pass #Windows is not actually supported at this point owing to complications in how Windows views its own filesystem.
	
def keyLoad(): #takes information gathered by findKeyfile and prints a confirmation message to screen, terminating if incorrect.
	foo = raw_input("Press enter to confirm that the system will use the key located at " + pathKey)
	keyFile = open(pathKey)
	keyData = keyFile.read()
	importResult = gpg.import_keys(keyData)
	debugPrint(importResult.count)
	print("Key imported. If program terminates irregularly, remove manually from GPG.")

		
def getContents(category, tgt): #populates a listing of all contents under target, based on OS, and their sizes.
	print("Currently walking the " + category + " directory.")
	for fromRoot, dirs, files, in os.walk(str(tgt)):
		for item in files:
			global sumSize
			global counterFID
			global listSection
			foo = counterFID + 1
			counterFID = foo
			metaTGT = os.path.join(fromRoot, item)
			size = os.path.getsize(metaTGT)
			fooSize = sumSize + size
			sumSize = fooSize
			listAbsolutePaths.update({str(counterFID):str(metaTGT)})
			listFSNames.update({str(counterFID):str(item)})
			listSizes.update({str(counterFID): str(size)})
			relativePath = metaTGT.replace(tgt, "~", 1) #removes tgt from the path string, leaving the path string after the root of TGT, including subfolders, for recovery.
			listRelativePaths.update({str(counterFID):str(relativePath)}) 
			listSection.update({str(counterFID):str(category)})
	
def makeIndex(): #takes the result of successive getContents calls and builds a single index containing all.
	global sortedFiles
	sortedFiles = sorted(listSizes, key=listSizes.__getitem__)
	sortedFiles.reverse()
	
def calcBlocks(): #takes the index and sorts it to allow the minimum number of blocks. Current method is not necessarily accurate but close enough for government work. (show's perfect number of blocks)
	global numBlocks
	numBlocks = int(math.ceil(float(sumSize)/float(blockSizeActual)))
	
def buildBlocks(): #successively generates new dirs for all blocks and fills them with their corresponding datasets
	global workDir
	if currentOS == "Windows": #identifies and builds the temporary working directory
		workDir = "C:/tapestry/" #TODO replace with a temp location
	if currentOS == "Linux":
		workDir = "/tmp/tapestry/"
	if not os.path.isdir(workDir):
		os.mkdir(workDir)
	os.chdir(workDir)
	building = True #starts the building process
	workIndex = sortedFiles
	activeBlock = 0 #number of the current block. Is a counter.
	isSpace = False #No block exists therefore no space in it!
	while building == True:
		if len(workIndex) == 0: #If there's nothing in the index, we can stop building.
			building = False
			print("Finished Building Blocks.")
		if isSpace == False:
			activeBlock+=1
			date = datetime.date
			activedir = str(str(workDir)+str(compid)+"-"+str(date.today())+"-"+str(activeBlock)+"/")
			os.mkdir(activedir)
			os.chdir(activedir)
			isSpace = True
			blockCapacity = blockSizeActual
		if isSpace == True:
			for item in workIndex:
				posItem = workIndex.index(item)
				itemStr = str(item)
				size = os.path.getsize(listAbsolutePaths[itemStr])
				if size <= blockCapacity: #Item fits on the lift and gets copied.
					shutil.copy2(listAbsolutePaths[itemStr], str(activedir))
					os.rename(str(listFSNames[itemStr]), itemStr) #renaming the file to its ID aids in recovery.
					bar = blockCapacity - size
					blockCapacity = bar
					lastSize = size
					del workIndex[posItem]
				if size >= (blockSizeActual): #This file will never fit in the block
					print("ERROR: " + str(listAbsolutePaths[item]) + " is too large to fit in a block and has been removed from the process.")
					del workIndex[posItem]
				if size > blockCapacity: #This file is too big and must be skipped.
					continue
		foo = len(workIndex) - 1
		if foo > 0:
			bar = workIndex[foo]
			global minimum
			minimum = os.path.getsize(listAbsolutePaths[bar]) #the final item in the list should be the smallest by size unless I've gone well mad.
		else:
			minimum = 0
		if minimum >= blockCapacity:
			isSpace = False
	sumBlocks = activeBlock #Need to turn this into a useful value for later
	listRecovery = [sumBlocks, listRelativePaths, listSection] #We need to pickle ALL these things at once.
	os.chdir(str(workDir+compid+"-"+str(date.today())+"-1/"))#The recovery indexes belong on the first disk, which might not be the only disk, so we have to go back.
	recPickle = os.open("recovery.pkl", os.O_CREAT|os.O_RDWR)#We need to make some files.
	filePickles = os.fdopen(recPickle, "w")
	pickle.dump(listRecovery, filePickles)#dumps the sectional category to block. RCV mode uses these two blocked indexes to put the files back where they were found.
	print(str(sumBlocks) + " blocks have been created.")
	
def tarBlocks(): # turns /blockN/ into blockN.tar.bz2 for all blocks, deleting the source directory.
	print("Packaging blocks per tar with bz2 compression.")
	os.chdir(workDir)
	for root, blocks, files in os.walk(workDir): #starts walking the blocks
		for block in blocks:
			with tarfile.open(str(block)+".tap", "w:bz2") as tar: #creates a dummy tar handler, naming the tarfile per the block name
				for foo, bar, files in os.walk(str(block)): #crusies the relevant dir
					for item in files:
						tar.add(workDir+block+"/"+item, arcname=item) #There is a cleaner way to do this but damned if I know what it is...
					tar.close()
			shutil.rmtree(block) #deletes the directory. Should be done immediately after each block is tarred otherwise the backup tripples the size of the data rather than doubling it
	print("Done.")
			 
def lockBlocks(): #encrypts the blocks via a call to GPG using the 'DRPub.key' as the public key of choice.
	print("Beginning blockwise encryption with the current GPG installation.")
	for fuckthat, noise, tars in os.walk(workDir):
		for tar in tars:
			with open(tar, "r") as p:
				tgtOutput = os.path.join(desktop, tar)
				debugPrint(tgtOutput)
				k = gpg.encrypt_file(p, fp, output=tgtOutput, armor = False, always_trust=True)
			print(tar + " Encrypted using the recovery key.")
	print("Cleaning up plaintext tars.")
	os.chdir(homeDir)
	
def remKey(): #removes the Key from the keyring.
	gpg.delete_keys(fp, True)
	gpg.delete_keys(fp)
	print("The recovery key has been deleted from the keyring.")
	
def getRecoveryDicts(): #parses the tarfile expected in CDrom, places it into temporary storage, and unpickles the recovery tables.
	for a, b, files in os.walk(blockDir):
		for file in files:
			if file == "recovery.pkl":
				foo = os.path.join(a,file)
				global recPaths
				global recSections
				global numVolumes
				listRecovery = pickle.load(open(foo))
				debugPrint(listRecovery)
				numVolumes, recPaths, recSections = listRecovery
	if len(recPaths) > 0: #Throws an internal error if the required files are not properly mounted and closes the program so that it will not damage the archive
		print("Found Recovery Table 1")
	else:
		print("There was a problem finding the file 'recPaths' on the disk. Please reload this program and try again, being careful to use Disk 1.")
		clearDown() #Deletes temporary files to prevent system bloat
		dropSecretKey() #removes the recovery secret key from the keyring per protocol
		exit()
	if len(recSections) > 0:
		print("Found Recovery Table 2")
	else:
		print("There was a problem finding the file 'recSections' on the disk. Please reload this program and try again, being careful to use Disk 1.")
		clearDown()
		dropSecretKey()
		exit()
	
def unpackDisk(): #unpacks across the currently-loaded block according to information in the recovery dictionaries, then deletes the current tarfile from memory
	for a, b, files in os.walk(blockDir):
		for file in files:
			if file == "recovery.pkl":
				continue
			if file == "tarball":
				continue
			catFile = recSections[file] 
			catActual = dirActual[catFile] #FIX//Not-A-Category problem
			relativePath = recPaths[file]
			fileDest = relativePath.replace("~", catActual, 1) #fileDestination
			if not os.path.isdir(os.path.dirname(fileDest)): #creates the destination folder if it doesn't already exist.
				os.makedirs(os.path.dirname(fileDest))
			shutil.copy2(os.path.join(a, file), fileDest)
	
def decryptDisk(): #decrypts the disk and extracts contents to tmp
	global workDir
	global diskMount
	if currentOS == "Windows": #Figure out what the hell we're doing and make some temp dirs.
		diskMount = "D:/"
		workDir = "C:/tapestry/"
	if currentOS == "Linux":
		diskMount = str("/media/"+uid+"/")
		workDir = "/tmp/tapestry/"
	if not os.path.isdir(workDir):
		os.mkdir(workDir)
	os.chdir(workDir)
	for a, b, files in os.walk(diskMount):
		debugPrint(files)
		for file in files:
			if file.endswith(".tap") == True: 
				global tgt
				tgt = workDir+file
				os.mkdir(workDir+file)
				outputTGT = str(workDir+file+"/tarball")
				with open(a+"/"+file, "rb") as k:
					debugPrint("Attempting to decrypt: " + k.name)
					baz = gpg.decrypt_file(k, output=outputTGT, always_trust=True)
					debugPrint("Decrypted: "+ str(baz.ok))
					if not baz.ok:
						debugPrint("Decryption Error: " + str(baz.status))
				unpacker = tarfile.open(workDir+file+"/tarball", "r|bz2")
				unpacker.extractall(path=workDir+file)
				unpacker.close()
			else:
				continue
	global blockDir
	blockDir = tgt
	debugPrint(blockDir)
	
def clearDown(): # Delete the tapestry tempfiles and clear the keyring.
	shutil.rmtree(workDir)
	remKey()
	
def debugPrint(contents): #prints messages during debug mode
	if args.debug:
		print(contents)
		
def genKey(): #generates a key with minimal user input, and puts them on the desktop.
	print("Generating a new recovery key, please stand by.")
	input_data = gpg.gen_key_input(key_type="RSA", key_length=2048, name_real=str(uid), name_comment="Disaster Recovery", name_email="nul@autogen.key")
	keypair = gpg.gen_key(input_data)
	debugPrint(keypair.fingerprint)
	fp = keypair.fingerprint #Changes the value of FP to the new key
	config.set("Environment Variables", "Expected FP", str(fp)) #sets this value in config
	with open("tapestry.cfg", "w") as cfg:
		config.write(cfg)
	os.chdir(desktop)
	pubOut = gpg.export_keys(fp)
	keyOut = gpg.export_keys(fp, True)
	pubFile = os.open("DRPub.key", os.O_CREAT|os.O_RDWR)
	pubHandle = os.fdopen(pubFile, "w")
	pubHandle.write(str(pubOut))
	pubHandle.close()
	keyFile = os.open("DR.key", os.O_CREAT|os.O_RDWR)
	keyHandle = os.fdopen(keyFile, "w")
	keyHandle.write(str(keyOut))
	keyHandle.close()
	print("The exported keys have been saved to the desktop. Please move them to removable media.")
	
	
def setup(): #the manual reconfiguration process packaged as a single function
	global setupMode
	setupMode = True
	while setupMode:
		print("Welcome to PatchTapestry Bespoke Backup Tool " + version)
		print("Setup Flag Detected.")
		print("Please Select from the following options:")
		print("1. Change User ID")
		print("2. Change Machine Label")
		print("3. Change Block Size")
		print("4. Directory Management")
		print("5. Quit")
		func = raw_input("Option:")
		if func == "1":
			print("Please enter the desired username.")
			uid = raw_input("Username:")
			config.set("Environment Variables", "uid", str(uid))
			print("New UID Set: " +uid)
		elif func == "2":
			print("The current machine label is: " + str(config.getopt("Encironment Variables", "compID")))
			print("Please enter the new label.")
			compID = raw_input("Machine Label:")
			config.set("Environment Variables", "compID", str(compID))
			print("The new label was set to :" + compID)
		elif func == "3":
			print("The Blocksize determines the maximum size in MB a .tap block can be.")
			print("It is recommended to choose a value 100 MB less than the capacity of your media.")
			print("Please enter a new blocksize in MB.")
			newSize = raw_input("Default is 4000:")
			config.set("Environment Variables", "blockSize", newSize)
		elif func == "4":
			print("The directory management function is under construction.")
			print("Your configuration file is at:")
			locationConfig = os.path.join(homeDir, "tapestry.cfg")
			print(str(locationConfig))
			print("Please edit this file directly to add, remove, or change target directories and their labels.")
		elif func == "5":
			print("Exiting Setup.")
			setupMode = False
			with open("tapestry.cfg", "w") as cfg:
				config.write(cfg)
		else:
			print("Your entry was not a valid option.")
			print("Please enter the number of the option you wish to execute.")
		
def init(): #the first-run setup process triggered by the absence of a config file
	print("Configuration file not found.")
	print("Beginning first-time setup.")
	print("To begin with, please provide your username on this system.")
	uid = raw_input("Username:")
	config.set("Environment Variables", "uid", str(uid))
	print("Next, enter a label to uniquely identify this computer.")
	compID = raw_input("CompID:")
	config.set("Environment Variables", "compID", str(compID))
	print("Please enter the desired blocksize in MB.")
	blockSize = raw_input("(4000)")
	config.set("Environment Variables", "compID", blockSize)
	print("Excellent. Tapestry will now create a default configuration file here:")
	print(str(homeDir))
	config.set("Default Locations/Nix", "Docs", "/home/"+uid+"/Documents")
	config.set("Default Locations/Nix", "Photos", "/home/"+uid+"/Pictures")
	config.set("Additional Locations/Nix", "Video", "/home/"+uid+"/Videos")
	config.set("Additional Locations/Nix", "Music", "/home/"+uid+"/Music")
	config.set("Default Locations/Win", "Docs", "C:/Users/"+uid+"/My Documents")
	config.set("Default Locations/Win", "Photos", "C:/Users/"+uid+"/My Pictures")
	config.set("Additional Locations/Win", "Video", "C:/Users/"+uid+"/My Videos")
	config.set("Additional Locations/Win", "Music", "C:/Users/"+uid+"/My Music")
	print("Please review this file. If you need to make any changes to the included backup")
	print("locations, please run the program again with the flag --setup.")
	with open("tapestry.cfg", "w") as cfg:
		config.write(cfg)
	exit()
	
#It's runtime bitches!
print("Welcome to PatchTapestry Bespoke Backup Tool " + version)
if args.setup:
	setup()
elif uninit == True:
	init()
elif args.rcv == False: #runtime for the backup compiling mode
	print("The program is currently configuring itself. Please wait.")
	findKeyfile("pub")
	if foundKey == True:
		keyLoad()
	else:
		print("Unable to find a supported key stored on USB drives attached to this machine.")
		plainOutput = raw_input("Generate a new PGP Key? y/n")
		if plainOutput == "n":
			print("Terminating.")
			exit()
		elif plainOutput == "y":
			genKey()
			exit()
	print("The program is scanning its target directories and calculating the structure of the archives.")
	print("You will be prompted for confirmation when this work is complete.")
	for category in listRun: #scans all the targets in the current run queue so that they can be fed to index
		getContents(category, listRun[category])
	makeIndex()
	calcBlocks()
	doIt = raw_input("The final archive is a total of " + str(sumSize/(2**20)) + "MB, in " + str(numBlocks) + " blocks. Please confirm this is available. Continue?")
	if doIt == "n":
		print("Terminating.")
		clearDown()
		exit()
	buildBlocks()
	tarBlocks()
	lockBlocks()
	clearDown()
	print("The archiving process is complete. Please prioritize burning the blocks to disk. This program will now terminate.")
	exit()
elif args.rcv ==True: #the runtime for the recovery mode
	print("Entering Recovery Mode. The program will now call GPG to mount the secret key.")
	findKeyfile("sec")
	if foundKey:
		keyLoad()
	else:
		print("An error has occurred during key mounting. Check that DR.key is available.")
	print("This program will unpack the backup in its original structure to the locations specified in the configuration variable block. Please consult source prior to unpacking.")
	raw_input("Please insert the first disk into the cd-rom drive and press any key to continue.")
	decryptDisk()
	getRecoveryDicts()
	debugPrint("Expecting "+str(numVolumes)+" disks.")
	while numVolumes > 0:
		unpackDisk()
		numvolumes = numVolumes - 1
		numVolumes = numvolumes
		if numVolumes > 1:
			raw_input("Please insert the next disk.")
			decryptDisk()
	print("All disks indicated have been unpacked.")
	clearDown()
	print("All work is complete. Please retain backup as normal.")
	exit()