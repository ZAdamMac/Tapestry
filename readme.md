# Tapestry (Specialized Backup Tool)

## Introduction

Patch's Tapestry is a bespoke data backup tool designed for a particular, butgenerally-acceptable, use case. Written in python, Tapestry uses Gnu Privacy Guard (GPG) to generate archive "blocks" from targeted directories on a given system and reproduce those blocks in a same-or-similar organizational format  upon restoration. The tool automatically subdivides the archive into blocks of a user-configurable size without breaking the content data (that is, the  structure of individual files is maintained). The blocks are then encrypted using the users Disaster Recovery PGP key and presented as ready-to-move. The intended use case is for backup to single-write physical media - though other use cases exist and are being actively developed for.

## Requirements
	-Python 3.5 or later
	-Python-gnupg
	-GnuPG 2 or later
	
## Contribution and Acknowledgement

Building Tapestry has been a large and time-consuming project, but it would have been even more so without the work of the developers of our dependancies - GnuPG, the Python-GnuPG module, and obvious python itself.

If you would like to contriubte to the development of Tapestry, feel free to start a pull request.
	
## Security Considerations
Tapestry relies on Gnu Privacy Guard - an implementation of the PGP protocol - in order to securely store the archives it generates, and also to provide a mechanism for verifying the individual who generated the backup. It does this using two seperate keys - the Encryption Key (sometimes called the "Disaster Recovery" key, after the comment included on keys Tapestry Generates) and an optional signing key specified by the user.

### Care and Feeding of the Disaster Recovery Key
When you run Tapestry for the first time, or otherwise cause it to generate a new key, the program will export the keys from GPG as two sperate files: `DR.key` and `DR-pub.key`. The former contains both the private and public keys of the RSA keypair - the latter contains only the public portion.

The private key and its associated file should be kept in a secure location - preferably either on removable media accessable only by trusted administrators or possibly on the keyring of a single-user/single-machine system, protected by a passphrase. **The use of passphraseless DR keys is considered harmful and should not be implemented.** It is even recommendable that you change the passphrase of the DR key regularly. If you are using the DR key across several systems, it is recommended that you also generate a revocation certificate (see GPG's docs) so that it can be revoked in the event of compromise.

By design, the public key can be widely distributed if desired, as it cannot be used to decrypt files it was used to encrypt. This is the useful property of the PGP protocol. In Tapestry's case, this may be useful for a number of reasons. You may desire to leave the public key on your keyring to run the program in keyring mode, or you may be working in an office environment where it would be useful to have the key stored on many machines at once. Using an asymetric protocol like this allows you this flexability. A public key cannot be said to be compromised, as it isn't even a secret.

### In the Event of a Compromise, Do Not Break Glass
It's possible that your `DR.key` file may be compromised through misuse, overuse, carelessness, or malicious action. Don't panic. If your archives are stored remotely and on removable media they will not be immediately accessable to an attacker. The decision to destroy these archives or not is ultimately up to the user.

If a physical compromise of your storage is not in your threat model, you can still issue the revocation certificate over your key server of choice, preventing further archives from being written to the corresponding public key. Doing only prevents new archives from being generated - the compromised key can still be used to open your files.

Do not simply change the passphrase - it will not save you now. Simply revoke and delete the old key, and generate a new one. A tool is under consideration in the future for retroactively recreating .tap archives to use your new key. At present, the only solution is to follow the usual recommendations in generating a fresh backup.

### Signing - Why and How
If you are a single user operating Tapestry on one machine and your threat model does not include the possibility of a forged archive being addressed to you, you do not need signing. 

However, if you are using Tapestry across many machines or you are concerned that your public key could be used to generate archives with malicious content, there is a solution, and it is part in parcel with the PGP protocol. In fact, it is the feature of cryptographic signatures that will allow future additions like a network storage mode to be used relatively safely.

A cryptographic signature can be generated alongside the backup itself at relatively little computational and storage overhead, and the use of signing is highly encouraged. If a file with a corresponding signature is modified after signing, attempts to verify the signature is failed. Similarly, only the person in possession of the *private* key of a keypair can sign a document, thereby verifying that they themselves did so, assuming they retain control of their key and follow best practices.

**A signature is not an assurance that there is no malicious code in the signed file or message.** It is merely an assurance of the identify of the person who signed the code. Under tapestry's use case, it is an assurance that the person who ran tapestry was in the possession of both the private key they used and its passphrase. ***Never*** *use a key with no passphrase for signing*. This practice is such a bad idea that Tapestry will choke and die if you try.

***As of 0.3.0 and prior "loopback pinentry" is being used to pass pins from Tapestry to GPG!*** If you have more and less sensitive keys to use for signing use your least sensitive one until a proper pinentry hooking method is implemented. A malicious actor sniffing the traffic on your machine's loopback interface may be able to capture packets revealing your PIN or Passphrase.

It may be desirable for example, to have a "I did this Tapestry Backup" signing key, used for nothing else, that you signed with your main key. If comrpomised, someone could still sign backups as you, but if they tried to sign an email, for example, it would look odd to the recipient. This is obviouslly a halfassed solution at best. Fixing this pinentry issue is the highest priority task in development of 0.3.1.

### How to Store Keys
I can't speak for everyone's use case and I'm also not an expert on the matter. I personally store the public key of the disaster recovery key on every device I intend to use it on. The private key lives on a USB drive along with a few tools I use for cleaning up computers, and can be imported if necessary. I also keep a paper copy of the private key.

As for my signing key, I am currently (perhaps wrongly) using my main signing key, which lives on an OpenPGP smart key. In point of fact, Tapestry is perfectly oblivious to how you choose to store your keys - if it can't import them from removable media and can't find them in your keyring it assumes they don't exist.
	
## Installation and First Time Setup
### Dependencies
If you are lacking any of the above requirements, please install them first. GPG is available on most Linux distros by default - under Windows, locate and install Gnupg4Win from the gnupg website. You may also need to install the latest python under windows. When doing so, be sure to also install pip.

In either event, it is likely you are missing python-gnupg. That's okay, we can get python modules using `pip` at the command line.

Under Linux:
```
    sudo pip install python-gnupg
    sudo pip3 install python-gnupg
```

Under Windows:
```
    python -m pip install python-gnupg
```

Once you have all the requirements installed it's time to go ahead with installing Tapestry itself.

###Installing Tapestry
It's important to note that as a python script, Tapestry strictly-speaking isn't something you "install", but it's still necessary to properly obtain and configure it.

**1. Begin by downloading the latest release of tapestry and its signature from the official github repo.** While older versions are made available for users of the older versions to aid recovery, it is always recommended to use the most recent release version. You should also download the corresponding signature file so that we can verify it. I'll show you how. If you haven't already, this is a good time to obtain the key with the fingerprint "FE7E 1DF0 3EC1 A278 FFDC 9E02 BE15 FA90 DB57 DFAC" from an appropriate keyserver. You'll need it to verify the package.

**2. Verify the signature.** Under windows this should be as easy as right-clicking on the signature and selecting verify - your GPG4Win install should have also installed a tool called Kleopatra. Linux users can use cleopatra as well, or they can open the terminal in the directory where they have stored the downloaded signature and file and run the following command:
    gpg --verify <sigfile>

If the files have not been tampered with and you have correctly imported the public key ending in "DFAC" or its corresponding master key you should recieve a message that the signature is valid. It may not be fully trusted - this is a limitation of GPG's web-of-trust principle and a sign that I am not getting enough people to sign my key!

**3. Unpack the archive.** When you downloaded a release version of the program you downloaded a tarfile and the signature of that tarfile. Whether you are using Windows or Linux, unpack the archive to a directory of your choosing.

**4. First-Time Configuration** The `tapestry.cfg` file among the extracted files is a duplicate of either my own personal configuration or the configuration of the test instance. Either way it won't do you much good. You can configure Tapestry by deleting this file and running it once, or, more efficiently, simply open the file in a text editor and make a few changes. *Note: Under windows' notepad.exe, your line breaks may be absent. Either add them back in for your own readability or use a text editor that supports unix line termination.*
 1.  The Environment Variable "uid" must match the username of the user who will be running Tapestry, as it appears in the directory structure.
 2. CompID can be any value, but you should make it something that would make sense to you. A discriptor or the machine's host name would both serve well. This is especially important if you are using network storage or don't intend to label your physical disks.
 3. Blocksize can be any size - the config file is expressed in MB. For most users the default should be sufficient - it ensures both the archive and its signature can be placed on the same single-layer DVD-R disk.
 4. The "expected FP" value can be set to 0. When Tapestry generates your DR key for you, it will automatically set this value to the value of the new key.
 5. "Sign by Default" controls the default signing of output files. ***It is very much recommended that signing of backups be done***. However, if you find this to be impractical (say, running Tapestry as an automated task at 3AM with the signing key on a smart card), you can set it to false, but I strongly encourage you to sign the backups before burning them. It is your only assurance that they haven't been tampered with since they were created.
 6. Set KeyringMode to true, if it isn't already. Use of the non-keyring mode is depricated and will likely be removed as early as v.0.3.1. **For the Time Being, set this to false on your first run of Tapestry to enable the new key generation process**
 7. Set the drive letter to the string pointing to your optical disk drive under Windows. If you are using Linux exclusively this value isn't important to you.
 8. Set any of the further values as you would like them, bearing in mind the following:
  - The directory path shown is the top of a recursive dive. All of its subdirectories will be included
  - category names "doc" should be duplicated where possible between /nix and /Win, but cannot be duplicated internally.
  - Default Locations will be backed up with a simple call to the program. Additional locations require the additional argument `--inc` to be passed at runtime.
 9. Save your configuration and consider backing it up to a spare removable drive now. You can still recover without a configuration file but the results won't be as tidy.
 10. Launch tapestry. The program will spin for a while and eventually prompt you for information it needs to make you a key, which will be output to a folder on the desktop. Double-check that this key is still in your keyring, and backup both copies of the key to another disk.
 11. Go back into config and set Keyring Mode back to true. This will be changed in a future version to obviate the need for this step and step 6.

Congratulations, Tapestry is now ready to use.

## Regular Use
During regular operation, Tapestry is pretty straightforward to use. The main choice is whether or not to invoke it using `--inc` or not. This is going to depend a lot on your threat model and backup policy. I use `--inc` about every 3 months, but my inclusive operation only adds music and videos to the list, and I don't use those much.

Tapestry can also be scheduled as a cron job or triggered using the Windows Task Scheduler.

Before running Tapestry, it is important to scan your computer for malware to ensure everything is good and clean before backing up, as Tapestry currently provides no means of ensuring the contents of a backup are "clean". Obviously, recovering from an infected backup would put you right back where to started, so check first!

## Recovery Options
Recovering under tapestry is as easy as making sure the correct secret key is available on the keyring, inserting one of the disks from a Tapestry backup, and running tapestry with the `--rcv` argument. Tapestry will automatically recover your files to the category locations defined in the local config file! If no location is given in `Tapestry.cfg`, that's okay - Tapestry will create a subdirectory in `~/Desktop/Tapestry Output` for that category and unpack your files there!


