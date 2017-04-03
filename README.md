# Patchs-Tapestry
Specialist Batch File Backup Tool
Introduction
---------------

Patch's Tapestry is a bespoke data backup tool designed for a particular, but generally-acceptable, use case. Written in python, Tapestry uses Gnu Privacy Guard (GPG) to generate archive "blocks" from targeted directories on a given system and reproduce those blocks in a same-or-similar organizational format upon restoration. The tool automatically subdivides the archive into blocks of a user-configurable size without breaking the content data (that is, the structure of individual files is maintained, though compressed). The blocks are then encrypted using the users Disaster Recovery PGP key and presented as ready-to-move. The intended use case is for backup to single-write physical media.

Requirements
---------------
	-Python 2.7 or later
	-Python-gnupg
	-GnuPG 2 or later
	
Getting Started
---------------

	A. First-Time Startup
	The first time you launch pTapestry, the script will check for the presence of a configuration file, tapestry.cfg. If it does not find this file, it will walk you through a simple initialization process and construct tapestry.cfg. It is particularly important to set the uid variable correctly - it MUST exactly match the username of the user which is running Tapestry, or the tool will fail to autogenerate backup paths correctly.
	
	B. Setup
	After the initialization run, run tapestry again with the "--setup" flag. You will be presented with a menu that walks you through setting the customizable variables on the program. 
	
	In the present version, it is necessary to edit tapestry.cfg manually to add, remove, or edit your backup directories.
	
	C. Generating your PGP Keys
	Tapestry relies on OpenPGP, as implimented in GnuPG, for its cryptographic aspects. It does so by generating a key with certain default parameters, with minimal user intervention, and saves them as two seperate files "DRPub.key" and "DR.key".
	
	DRPub.key contains only the "public", or encrypting, key. A compromise of DRPub.key's security would not compromise the security of your backup process in most cases - see the caveats section. If you are using Patch's Tapestry as an organizational backup tool, it is perfectly acceptable to widely distribute DRPub.key.
	
	DR.key contains the "secret" key, which is necessary to decrypt backups created with Tapestry. A full briefing on PGP key security is beyond the scope of this document, but DR.key should be in the hands of as few individuals as possible.
	
	Tapestry looks for both files on removable media ONLY. Future versions may first check the PGP keyring. The current version of Tapestry also does not tell you if someone has exchanged your particular key for a different one, compared to the last time it was run. Such an alert is planned for future implementation.
	
	D. Caveats
	There are still a few unresolved security issues with pTapestry. Tapestry's config file presently doesn't self-diagnose changes or other incorrectness.
	
	It is possible to use a larger (and therefore more notionally secure) key as DR.key and DRPub.key if desired. Such a key would have to be generated manually using GPG. Tapestry has no way of knowing which key you wanted to use at this point, and you would then need to replace the "expected FP" variable in tapestry to match the fingerprint of the new key. A future version will allow key configuration in greater detail and obviate this step.
	
	Due to security designs in "GPG2", Tapestry (currently) cannot rely on keys with passphrases for operation, at least not in any supported way. Therefore, it is advisable to use a robust signing key to certify the contents of the backup upon creation, to ensure they have not been altered in any way. This, plus good security in the storage and handling of the Disaster Recovery Keys, should allow reasonable assurance of both the integrity and secrecy of the backup. See the main information page for more information on design philosophy.
