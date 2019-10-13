"""
A simple script to generate a small, structured corpus of files. Improves upon
the original by accepting CLI arguments and being platform agnostic.
"""


import argparse
import os
import random
from string import printable as characters

__version__ = "2.0.0"


def parse_args():
    """Parse the arguments given to the script/module at runtime for later use.
    
    :return: Tuple of arguments set to variables for use later in the script.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', help="absolute or relative path to the top level of the corpus", action="store")
    parser.add_argument('-p', help="number of files to generate in each directory", action="store")
    parser.add_argument('-d', help="comma-delimited string defining a list of directories to create to structure the data", action="store")
    parser.add_argument('-l', help="length of each file, in words. Noisy but direct correlation to overall file size", action="store")

    args = parser.parse_args()
    root_path = args.r
    file_count_per_folder = int(args.p)
    directory_list = args.d.split(",")
    file_length = int(args.l)

    return root_path, file_count_per_folder, directory_list, file_length


def create_folder_heirarchy(dir_list):
    for each in dir_list:
        if not os.path.exists(each):
            os.mkdir(each)
    print("Done creating directories.")


def populate_corpus_files(files_count, file_length):
    print("Beginning corpus file generation. This could take a while.")
    files_spawned = 0
    for a, extant_dirs, files in os.walk(os.getcwd()):
        total_files = files_count * len(dirs)
        for current_dir in extant_dirs:
            for each in range(0, files_count):
                files_spawned += 1
                print("Now generating file %s of %s" % (files_spawned, total_files))
                file_name = os.path.join(current_dir, str(files_spawned))
                generate_file(file_name, file_length)
    print("Done generating files. The script will now exit.")
    exit(0)


def generate_file(name, length):
    with open(name, "w") as f:
        for each in range(0, length+1):
            word_length = random.randint(5, 20)
            word = ""
            for char in range(word_length):  # build a word out of random characters
                random.seed(os.urandom(256))
                next_char = random.choice(characters)
                word += next_char
                f.write(word)


if __name__ == "__main__":
    root, per_folder, dirs, file_words = parse_args()
    print("Corpusmaker %s is now deployed, targeting the %s directory" % (__version__, root))
    os.chdir(root)
    create_folder_heirarchy(dirs)
    populate_corpus_files(per_folder, file_words)
