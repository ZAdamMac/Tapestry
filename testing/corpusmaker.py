# Just a simple tool for making a corpus of compressible files of some given bounds.
# Properly maintained outside this repo as a scriptlet, but included here for clarity
# This version was tweaked specifically for use with Tapestry. If desired, the general solution can be provided.
# This script is not multiplatform; it's dependant on linux.

import os.path
import random

global dest; dest = "/home/patches/Desktop/Tapestry FT Data/Control/Corpus" # some pathlike destination to be root
global num; num = 10 #Number of files to include per category
global sizeEach; sizeEach = 1000000 # Desired file size in lines
global subdirs; subdirs = ["documents", "photos", "music", "videos"]

if not os.path.exists(dest):
	os.mkdir(dest)
os.chdir(dest)

src = open("/usr/share/dict/words", "r").read().splitlines()
bound = len(src)-1

for subdir in subdirs:
    if not os.path.exists(os.path.join(dest, subdir)):
        os.mkdir(os.path.join(dest,subdir))
    os.chdir(os.path.join(dest, subdir))
    for i in range(1, num+1):
        with open(str(i), "w") as file:
            for line in range (0, sizeEach):
                line = str(" ")
                for i in range (0, 12):
                    line = line+str(src[random.randint(0, bound)])+" "
                file.write(line)
            file.close()