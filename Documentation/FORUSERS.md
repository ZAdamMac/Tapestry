# Tapestry Specialist Backup Tool - User Documentation
*General-Use Documentation, prepared for Version 2.0.2*
*Some documentation applies only to 2.1, which is the development release. It is noted clearly as such.*

The goal of this specific documentation file is to provide a general overview and basic use cases for tapestry. More information about special use cases and considerations can be found in `FORADMINS.md`

## Full System Requirements
Tapestry is a reasonably lightweight and flexible script in its essence, but it does involve some basic requirements.

**Suggested Minimum Hardware Requirements**
- 4 GB RAM (Probably will run in less)
- 3.0 GHz, 64-Bit Dual-Core Processor (or equivalent)
- 10 GB or more unused Hard Drive Space

**Software Requirements**
- Python v3.5 or Later
- Python-GnuPG, v.0.4.2 or later
- GnuPG 2.1.11 or Later

### Other Considerations
Tapestry runs can be fairly long - on the order of 12 minutes per default-sized block, depending on your system resources and the amount of other processes running concurrently. Accordingly it's considered helpful to use cron jobs or other automation in order to run the backup overnight or during other periods of low-activity uptime. This has some special use considerations - see Documentation/FORADMINS.md for details

It is currently required due to software limitations that the recent version of GnuPG is installed as the primary instance. That is to say, a call to `gpg` should instantiate the latest version of it installed.

## Complete Explanation of Configuration
Tapestry stores its user-adjustable configuration files in a file which it expects to find at a path specified following the `-c` flag when invoked at runtime, like this:
```commandline
python3 -m tapestry -c /path/to/tapestry.cfg
```

This is an INI file whose categories and values are defined below.

### Environment Variables

|Option|Default|Use|
|---|---|---|
|**UID**|Set by user during setup()| the expected user identifier, used to autogenerate paths during setup. As setup has been to be deprecated, the UID tag likely will be as well.
|**compID**|Set by user during setup()| The "label" to assign to backups generated using this particular tapestry instance. Suggested use is either your organization's workstation identifier or the system hostname. This will be public-facing as part of the output filename.
|**blocksize**|4096| The size of the expected output files, before compression, in MB. Suggested value depends on intended storage medium. Since files greater than this size value will not be backed up, setting this value is a matter of personal requirement.|
|**expected fp**|set by --genkey|The fingerprint of the **disaster recovery key** encoded as a string. This is to be clarified in a future refactor|
|**sign by default**|true|Boolean value as to whether or not the system should use signing. Set to true by default. Highly recommended not to disable it except in some circumstances covered in the admin documentation.|
|**signing fp**|None|Set by the user, this is the hex string Fingerprint of the intended signing key. Should be different than the disaster recovery key, preferably specific to the user.|
|**recovery path**|`/media/`|The directory used to determine the mount point or other location of the .tap files expected by the recovery mode. Particularly in windows environments, this will likely need to be changed.|
|**output path**|No Default|The directory to which tapestry is to deliver the final packaged .tap files, and other outputs like the skipped file log or keys exported during --genKey|
|**keysize**|2048|The size of key to generate during --genKey and as part of first time setup. 2048 is the minimum viable, and therefore sane, default.
|**use compression**|True|Toggles the use of Tapestry's built-in bz2 compression handler. If set to true, blocks are compressed before encrypting to keep them under the blocksize.|
|**compression level**|2|A value from 1-9 indicating the number of bz2 compression passes to be used. Experimentation is required for different blocksizes to determine the minimum viable value. 9 passes is maximally efficient, but also takes considerable time, especially on larger blocksizes.|
|**Build-Time File Validation**|True| Controls whether or not the additional validation step will be done after the tarfile is built. This step ensures that the tarbuild process did not modify the contents of the backup files in any way.|

### Network Configuration
|Option|Default|Use|
|---|---|---|
|**mode**|none|Determines whether or not the FTP mode will be used. "none" for no network mode, "sftp" for the SFTP mode.|
|**server**|localhost|Determines the address of the server for the FTP mode|
|**port**|22|Determines the port at which the FTP server is listening.|
|**username**|ftptest|Username to use when authenticating to server - user will be prompted for a password at runtime. Can be blank|
|**auth type**|passphrase|Accepts `passphrase` and `key`, controlling whether a passphrase or key would be used to to network operations. If network operations are needed and the auth type is passphrase, the user will be prompted for the passphrase at the start of the run.|
|**credential has passphrase**|True|If true, the user will be prompted for the passphrase at the bginning of the run.|
|**credential path**|"/dev/null"|The path to a keyfile to be used to authenticate SFTP requests.
|**remote drop location**|drop|The path appended to all file upload requests. Should be blank in the reference implementation.|
|**keep local copies**| True| If false, Tapestry will delete the local copy of each block and signature upon upload.|


### Additional Categories
Additionally, the user will find categories for windows and linux options, indicating they are either "default" or "additional" locations for backup. Any number of these definitions can be included at the user's discretion, so long as each option label is unique. When doing this it is desirable to set equivalent paths for both OS varieties to improve final portability, but this is not strictly required.

## Runtime Arguments
Tapestry supports the following arguments at runtime:

|argument|function|
|---|---|
|--genKey|Generate a new RSA public/private keypair designed to be used as the Disaster Recovery Key. In a pinch this could also be used to generate a signing key, but there are better ways to do that.|
|--inc|Performs an "inclusive run", adding all of the "additional locations" categories to the work list at runtime. Provides non-granular differentation between "quick" and "complete" backups.|
|--rcv|Places the script in recovery mode, checking its recovery path for .tap files and their associated .sigs and recovering them programatically.
|--debug|Increases the verbosity of both Tapestry and its gpg callbacks for light debugging purposes|
|-c| the string which immediately follows should be a path to a configuration file.|

If no runtime arguments are provided the program assumes you intended to do a "basic build", and runs the backup routine using only the relevant "default locations" list.

## Key Security
Tapestry relies on a two-asymmetric-key system for its protection, as a mechanism to eliminate the need for trust between the user and their storage solution. Tapestry is currently designed to produce only its own key automatically - for the moment it is taken as read that the user would know how to develop a signing key. Specific instructions for signing key generation can be found in the GnuPG manpage or their online documentation. For the purposes of this section, it will be enough to concern the active and passive key security considerations.

### Key Size and Passphrase
By default, Tapestry creates a 2048-bit key when prompted to. This is the smallest common-size key we believe to be reasonably secure. If desired, this figure can be increased, though this is not recommended as it would impact both key generation and overall cryptographic operation time. With cryptography being the second-most computationally-expensive part of the system, and 4096-bit keys being excessive, we have settled on 2048 bit.

All keys use should be protected by a strong passphrase of at least 24 characters.

### Key Storage
Tapestry expects to find the keys it is looking for on the default gnupg keyring, found under `~/.gnupg/`. There is currently no plan in the works to change this.

Additionally, it is important to keep a master copy of the disaster recovery key offline and secure at all times as a backup. If you should happen to lose this key, your backups are unrecoverable.

### Passphrase Security
Tapestry, and Kensho Security Labs, endorse long passphrases punctuated randomly and including numerals for key passphrases.

Tapestry itself never handles a passphrase you provide it, either for recovery decryption or signing of backups, or indeed for key generation. This is the reason for the requirement for a recent version of GnuPG to be installed. Tapestry provides the command for the operation to GPG without a passphrase, prompting newer versions of GPG to respond by invoking the pinentry program they are configured to use. On most OS integrations this presents as a system window appearing, asking for the passphrase.

# Selecting your "Locations"
Tapestry treats every location defined in its configuration file as the top of an `os.walk()` command. This means, in practical terms, that everything in every subdirectory of that location will be backed up. Therefore, it is important to consider if any symbolic links are going to be followed that may end up with unintended consequences.

The specific locations you select are entirely up to you. At time of writing I personally use the documents and photos default folders in my default locations list, with my additional locations list including videos, music, and a subset of the hidden configuration directories.

## Network Storage Mode
Tapestry is designed to use two different networking modes - Networked File Systems, and FTP over TLS.

### Using Tapestry with NFS
Using Tapestry with any variation of a network filesystem is as simple as ensuring the desired device or drive is mounted to the local filesystem and setting the desired output directory on that device as Tapestry's output directory. No other networking configuration is necessary and the mode value should be `none`

### Using Tapestry with FTP/S
***Deprecated from 2.1***: *FTP/S Support is being dropped by Tapestry in the 2.1.0 release in favour of the more common, and arguably more secure, SFTP protocol*
Using Tapestry with FTP is a little more complex. Tapestry is designed primarily to work with TLS-secured FTP servers such as vsftpd. To configure this mode, make the following settings under Network Configuration:
- Set `mode = ftp`
- Set server and port per the configuration of your server.
- If necessary, provide a username to authenticate as.
- It is recommended you leave `keep local copies` set to True.

### Using Tapestry Exit Codes
***New in 2.1***: Tapestry provides OS-level exit codes based on events encountered during its run. For the most part, these exit codes represent particular error conditions, which are given distinct exit codes. You can intercept these with your automation in order to add your own additional error handling should issues arise.

|Exit Code|Meaning|
|---|---|
|0|Tapestry completed the requested operation successfully.|
|1|Tapestry attempted to validate or recover from a particular tapfile, but there was an issue with its recovery index file and it was unable to do so. This typically means that this is a very old Tapfile, generated pre-0.3.0.|
|2|Tapestry was attempting to validate or recover a particular tapfile and encountered an error in decryption that prevented it from doing so. Usually, this is a simple matter of not having the appropriate key on your keyring.|
|3|Tapestry was unable to locate the requested config file, or identify a fallback config file. Therefore, it has created a new one within its CWD. You should update this file or review your configuration path in the command to make sure you have a valid config file available.|
|4|Tapestry was unable to find the key that is configured as the encryption key on the keyring. Because of this it couldn't have proceeded with its operations and has exited accordingly.|
|5|Tapestry encountered some manner of network error in attempting to use the SFTP module functionality.|
|6|The keyring does not contain some value that Tapestry expected. If run interactively the missing value will be printed to stdout.|
