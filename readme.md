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
	
Getting Started
---------------

	A. First-Time Startup
	The first time you launch pTapestry, the script will check for the presence of
	a configuration file, tapestry.cfg. If it does not find this file, it will 
	walk you through a simple initialization process and construct tapestry.cfg. 
	It is particularly important to set the uid variable correctly - it MUST 
	exactly match the username of the user which is running Tapestry, or the tool
	will fail to autogenerate backup paths correctly.
	
	
	B. Setup
	After the initialization run, run tapestry again with the "--setup" flag. You
	will be presented with a menu that walks you through setting the customizable 
	variables on the program. 
	
	In the present version, it is necessary to edit tapestry.cfg manually to add, 
	remove, or edit your backup directories.
	
	NOTE TO USERS OF GPG v 2.0 AND ABOVE: Automated signing functionality depends 
	on a presently-blocked option. You can enable this functionality in modern 
	versions of GPG by adding "allow-loopback-pinentry" to your gpg-agent.conf
	file. Doing so presents privacy implications you may find undesirable and I 
	urge you to consider that possibility before continuing.
	
	C. Updating from Previous Versions
	It is advisable, if updating from a previous version, to first run the program
	in --setup and visit each config option in turn to ensure the correct values
	can be found in tapestry.cfg.
	
	Alternatively you can assign those values manually by simply modifying the
	packaged config file.
	
	D. Generating your PGP Keys
	Tapestry relies on OpenPGP, as implimented in GnuPG, for its cryptographic 
	aspects. It does so by generating a key with certain default parameters, with
	minimal user intervention, and saves them as two seperate files "DRPub.key" 
	and "DR.key".
	
	DRPub.key contains only the "public", or encrypting, key. A compromise of 
	DRPub.key's security would not compromise the security of your backup process 
	in most cases - see the caveats section. If you are using Patch's Tapestry as 
	an organizational backup tool, it is perfectly acceptable to widely distribute
	DRPub.key.
	
	DR.key contains the "secret" key, which is necessary to decrypt backups 
	created with Tapestry. A full briefing on PGP key security is beyond the scope
	of this document, but DR.key should be in the hands of as few individuals as 
	possible - preferably only the people who will actually handle recovering from
	backups.
	
	Tapestry looks for both files on removable media ONLY. It then checks the
	fingerprint of the key it finds against the last approved fingerprint that was
	used, to ensure the key has not been altered or replaced. It is possible to
	continue past the error message this generates if desired. Doing so resets the
	expected fingerprint value.
	
	The relatively unsecured nature of the DR key is covered by the use of digital
	signatures. It is intended for each user to sign the .tap blocks they generate
	with their own personal PGP key or subkey - a signature that can then be
	validated using the public version of their key on the part of those who are
	recovering these backups. Again, a primer on PGP key security is beyond the
	scope of this document - the signing keys can be made as secure as thought
	necessary.
	
	The lone exception is in the event the signing key is to be stored on an
	OpenPGP-compliant smart card device that supports "touch-only" operation, 
	such as a Yubikey. As Tapestry has no way to emulate a touch event, nor should
	it, using such a key is unlikely to be supported in any convenient way.
	
	D. Caveats
	There are still a few unresolved security issues with pTapestry. Tapestry's 
	config file presently doesn't self-diagnose changes or other incorrectness.
	
	It is possible to use a larger (and therefore more notionally secure) key as 
	DR.key and DRPub.key if desired. Such a key would have to be generated 
	manually using GPG. Tapestry has no way of knowing which key you wanted to use
	at this point, and you would then need to replace the "expected FP" variable 
	in tapestry to match the fingerprint of the new key. A future version will 
	allow key configuration in greater detail and obviate this step.
	
	Further, Tapestry does not rely on a secure pinentry program. Your passphase 
	may remain in memory. It is recommended to either restrict signing to trusted,
	known-secure machines or to use a subkey to sign the blocks. The truly 
	paranoid may wish to sign manually using the gpg2 CLI and its native pinentry.
	More robust passphrase-handling procedures are planned for future releases.
	
	Presently, to enable the use of the default-signing feature, Tapestry will
	attempt to autodetect whether or not "allow-loopback-pinentry" is in the
	user's gpg-agent.conf file. It will display a warning if it is absent and
	offer to ammend the file accordingly. For most users this is suffcient,
	however, loopback pinentry is not whitelisted. If it is enabled, any program
	running on the computer can call to that gpg instance and access the pinentry
	socket invisibly. This allows retry attacks to be launched against keys in the
	user keyring, possibly without the knowledge of the user. Steps taken to
	mitigate this risk are beyond the explicit scope of this document. Solutions
	include disallowing the behavior by default, or manual signing.