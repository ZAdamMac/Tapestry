# Tapestry (Specialized Backup Tool)

## Introduction

Tapestry is a bespoke data backup tool designed to provide secure and reliable backups without the need to trust the storage media/device. Written in python, Tapestry uses Gnu Privacy Guard (GPG) to generate archive "blocks" from targeted directories on a given system and reproduce those blocks in a same-or-similar organizational format  upon restoration. The tool automatically subdivides the archive into blocks of a user-configurable size without breaking the content data (that is, the  structure of individual files is maintained). The blocks are then encrypted using the users Disaster Recovery PGP key and presented as ready-to-move.

Full documentation is available as part of DOCUMENTATION.md

## Requirements
	-Python 3.6.7 or later
	-Python-gnupg 0.4.2
	-GnuPG 2 or later, installed as default
	
## Contribution and Acknowledgement

Building Tapestry has been a large and time-consuming project, but it would have been even more so without the work of the developers of our dependencies - GnuPG, the Python-GnuPG module, and obvious python itself.

If you would like to contribute to the development of Tapestry, feel free to submit a pull request, or perhaps buy me a coffee at [ko-fi.com/arclabs](https://ko-fi.com/arclabs), or consider backing [@ZAdamMac on Github Sponsors](https://github.com/users/ZAdamMac/sponsorship.)
	
## Security Considerations
Tapestry relies on Gnu Privacy Guard (GPG), a well-known FOSS implementation of the PGP protocol, in order to securely store the archives it generates, and also to provide a mechanism for verifying the individual who generated the backup. It does this using two separate keys - the Encryption Key (sometimes called the "Disaster Recovery" key, after the comment included on keys Tapestry generates) and an optional, though strongly recommended, signing key specified by the user.

### Care and Feeding of the Disaster Recovery Key
When you run Tapestry with the `--genKey` flag the program will export a new Disaster Recovery key from GPG as two separate files: `DR.key` and `DR-pub.key`. The former contains both the private and public keys of the RSA key-pair - the latter contains only the public portion.

The private key and its associated file should be kept in a secure location - preferably either on removable media accessible only by trusted administrators or possibly on the keyring of a single-user/single-machine system, protected by a pass-phrase. **The use of DR keys without pass-phrases is considered harmful and should not be implemented.** It is even recommendable that you change the pass-phrase of the DR key regularly. If you are using the DR key across several systems, it is recommended that you also generate a revocation certificate (see GPG's docs) so that it can be revoked in the event of compromise.

By design, the public key can be widely distributed if desired, as it cannot be used to decrypt files it was used to encrypt, and public keys are not meant to be held as secret anyway.

### Reacting to Key Compromises
It's possible that your `DR.key` (private half) file may be compromised through misuse, overuse, carelessness, or malicious action. Don't panic. If your archives are stored remotely and on offline, removable media they will not be immediately accessible to an attacker, necessarily. The decision to destroy these archives or not is ultimately up to the user.

If a compromise of your key storage is not in your threat model, you can still issue the revocation certificate over your key server of choice, preventing further archives from being written to the corresponding public key. Doing only prevents new archives from being generated - the compromised key can still be used to open your files.

Do not simply change the passphrase - it will not save you now. Simply revoke and delete the old key, and generate a new one. A tool is under consideration in the future for retroactively recreating .tap archives to use your new key. At present, the only solution is to follow the usual recommendations in generating a fresh backup.

### Signing - Why and How
If you are a single user operating Tapestry on one machine and your threat model does not include the possibility of a forged archive being addressed to you, because you are only storing your archives offline and in a space you physically control, you do not need signing. 

However, if you are using Tapestry across many machines or you are concerned that your public key could be used to generate archives with malicious content, there is a solution, and it is part in parcel with the PGP protocol. In fact, it is the feature of cryptographic signatures that will allow future additions like a network storage mode to be used relatively safely.

A cryptographic signature can be generated alongside the backup itself at relatively little computational and storage overhead, and the use of signing is highly encouraged. If a file with a corresponding signature is modified after signing, attempts to verify the signature is failed. Similarly, only the person in possession of the *private* key of a keypair can sign a document, thereby verifying that they themselves did so, assuming they retain control of their key and follow best practices.

**A signature is not an assurance that there is no malicious code in the signed file or message.** It is merely an assurance of the identify of the person who signed the code. Under tapestry's use case, it is an assurance that the person who ran tapestry was in the possession of both the private key they used and its passphrase. ***Never*** *use a key with no passphrase for signing*. This practice is such a bad idea that Tapestry will choke and die if you try.

Tapestry cannot see the passphrase you use to unlock your signing key. Instead, we trust the local GPG installation's existing pinentry configuration to launch the appropriate pin-entry binary to collect the passphrase and unlock the key.


### How to Store Keys
I can't speak for everyone's use case and I'm also not an expert on the matter. I personally store the public key of the disaster recovery key on every device I intend to use it on. The private key lives on a USB drive along with a few tools I use for cleaning up computers, and can be imported if necessary. I also keep a paper copy of the private key.

As for my signing key, I am currently using my main signing key, which lives on an OpenPGP smart key. In point of fact, Tapestry is perfectly oblivious to how you choose to store your keys - if it can't find them in your keyring it assumes they don't exist.
	
## Installation and First Time Setup
### Dependencies
If you are lacking any of the above requirements, please install them first. GPG is available on most Linux distros by default.

In any event, it is likely you are missing python-gnupg. That's okay, we can get python modules using `pip` at the command line.

Under Linux:
```
    sudo pip install python-gnupg
    sudo pip3 install python-gnupg
```

Once you have all the requirements installed it's time to go ahead with installing Tapestry itself.

### Installing Tapestry
The following steps are for if you wish to download Tapestry's source files and install them locally. You can install tapestry all in one step using pip, for example: `python3.6 -m pip install tapestry`. This will always get you the current production-release version.

**1. Begin by downloading the latest release of tapestry and its signature from the official github repo.** While older versions are made available for users of the older versions to aid recovery, it is always recommended to use the most recent release version. You should also download the corresponding signature file so that we can verify it. I'll show you how. If you haven't already, this is a good time to obtain the key with the fingerprint "E122 9B2A 2DF4 F2FE 50A5 A23F F373 FF4B 43FC 742F" from an appropriate keyserver. You'll need it to verify the package.

**2. Verify the signature.** Linux users can use Kleopatra, or they can open the terminal in the directory where they have stored the downloaded signature and file and run the following command:
    `gpg --verify <sigfile>`

If the files have not been tampered with and you have correctly imported the public key belonging to Zachary Adam-MacEwen or its corresponding master key you should receive a message that the signature is valid. It may not be fully trusted - this is a limitation of GPG's web-of-trust principle and a sign that I am not getting enough people to sign my key!

**3. Unpack the archive.** When you downloaded a release version of the program you downloaded a tarfile and the signature of that tarfile. Unpack the archive to a directory of your choosing - it makes no real difference to Tapestry's Operation.

**4. Install Tapestry From Source** Point your command prompt at the directory where you unpacked tapestry and run the following commands:
```commandline
python setup.py sdist bdist_wheel
pip install .
```

Once done, you can delete everything you unpacked except the tapestry.cfg configuration file, which you'll need.

**4. First-Time Configuration** The `tapestry.cfg` file among the extracted files is a duplicate of either my own personal configuration or the configuration of the test instance. Either way it won't do you much good. Simply open the file in a text editor and make a few changes: 
 1.  The Environment Variable "uid" *must* match the username of the user who will be running Tapestry, as it appears in the directory structure.
 2. CompID can be any value, but you should make it something that would make sense to you. A descriptor or the machine's host name would both serve well. This is especially important if you are using network storage or don't intend to label your physical disks.
 3. Blocksize can be any size - the config file is expressed in MB. For most users the default should be sufficient - it ensures both the archive and its signature can be placed on the same single-layer DVD-R disk.
 4. The "expected FP" value can be set to 0. When Tapestry generates your DR key for you, it will automatically set this value to the value of the new key.
 5. "Sign by Default" controls the default signing of output files. ***It is very much recommended that signing of backups be done***. However, if you find this to be impractical (say, running Tapestry as an automated task at 3AM with the signing key on a smart card), you can set it to false, but I strongly encourage you to sign the backups before burning them. It is your only assurance that they haven't been tampered with since they were created.
 7. Set any of the further values as you would like them, bearing in mind the following:
  - The directory path shown is the top of a recursive dive. All of its subdirectories will be included
  - category names ("doc") should be duplicated where possible between /nix and /Win, but cannot be duplicated internally.
  - Default Locations will be backed up with a simple call to the program. Additional locations require the additional argument `--inc` to be passed at runtime.
 8. Set the recovery and output paths as desired. **If you are recovering from physical media, set the recovery path to `/media/` or the drive letter for the device.**
 9. Save your configuration and consider backing it up to a spare removable drive now. It's possible to recover without your original configuration file, but not nearly as easy.
 10. Launch tapestry with the argument `--genKey`. This will cause the program to generate and export the keys you need in order to operate it. (You may then delete the secret key from the keyring manually at your own discretion).

Congratulations, Tapestry is now ready to use.

## Regular Use
***Note: After 2.0.0, all runs of Tapestry MUST include a reference to a configuration file in the format `-c <some config file>`!***

During regular operation, Tapestry is pretty straightforward to use. The main choice is whether or not to invoke it using `--inc` or not. This is going to depend a lot on your threat model and backup policy. I use `--inc` about every 3 months, but my inclusive operation only adds music and videos to the list, and I don't change those directories often.

Tapestry can also be scheduled as a cron job or triggered using the Windows Task Scheduler.

Before running Tapestry, it is important to scan your computer for malware to ensure everything is good and clean before backing up, as Tapestry currently provides no means of ensuring the contents of a backup are "clean". Obviously, recovering from an infected backup would put you right back where to started, so check first!

## Recovery Options
Recovering under tapestry is as easy as making sure the correct secret key is available on the keyring, or otherwise present, inserting one of the disks from a Tapestry backup, and running tapestry with the `--rcv` argument. Tapestry will automatically recover your files to the category locations defined in the local config file! If no location is given in `Tapestry.cfg`, that's okay - Tapestry will create a subdirectory in its output directory for that category and unpack your files there!

