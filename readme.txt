Introduction
---------------

Patch's Tapestry is a bespoke data backup tool designed for a particular, but
generally-acceptable, use case. Written in python, Tapestry uses Gnu Privacy 
Guard (GPG) to generate archive "blocks" from targeted directories on a given
system and reproduce those blocks in a same-or-similar organizational format 
upon restoration. The tool automatically subdivides the archive into blocks of
a user-configurable size without breaking the content data (that is, the 
structure of individual files is maintained, though compressed). The blocks are
then encrypted using the users Disaster Recovery PGP key and presented as ready
-to-move. The intended use case is for backup to single-write physical media.

Requirements
---------------
	-Python 2.7 or later
	-Python-gnupg
	-GnuPG 2 or later
	
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