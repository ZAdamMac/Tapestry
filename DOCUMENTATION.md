# Tapestry Specialist Backup Tool
*User Documentation, prepared for Version 1.0*

## Full System Requirements
Tapestry is a reasonably lightweight and flexible script in its essence, but it does involve some basic requirements.

**Suggested Minimum Hardware Requirements**
- 6GB RAM (or 1.5*Blocksize, if changing blocksize)
- 3.0 GHz, 64-Bit Dual-Core Processor (or equivalent)
- 10 GB or more unusued Hard Drive Space

**Software Requirements**
- 64-bit Linux/Unix-Based OS (Recommended)
- Python v3.7
- Python-GnuPG, v.0.4.2 or later
- GnuPG 2.1.11

### Other Considerations
Tapestry runs are fairly long - on the order of 20 minutes for a single 5GB block, or longer, depending on your system resources and the amount of other processes running concurrently. Accordingly it's considered helpful to use cron jobs or other automation in order to run the backup overnight or during other periods of low-activity uptime.

It is currently required due to software limitations that the recent version of GnuPG is installed as the primary instance. That is to say, a call to `gpg` should instantiate the latest version of it installed.

## Complete Explanation of Configuration
*Tapestry stores its user-adjustable configuration files in `tapestry.cfg` which it expects to find in the same directory. If you are testing against a development version of tapestry, it will instead look for `tapestry-test.cfg` in the same area.

### Environment Variables

|Option|Default|Use|
|---|---|---|
|**UID**|Set by user during setup()| the expected user identifier, used to autogenerate paths during setup. As setup is soon to be deprecated, the UID tag likely will be as well.
|**compID**|Set by user during setup()| The "label" to assign to backups generated using this particular tapestry instance. Suggested use is either your organization's workstation identifier or the system hostname.
|**blocksize**|4096| The size of the expected output files, before compression, in MB. Suggested value depends on intended storage medium. Since files greater than this size value will not be backed up, setting this value is a matter of personal requirement.|
|**expected fp**|set by --genkey|The fingerprint of the **disaster recovery key** incoded as a string. This is to be clarified in a future refactor|
|**sign by default**|true|Boolean value as to whether or not the system should use signing. Set to true by default. Highly recommended not to disable it for any reason.|
|**signing fp**|None|Set by the user, this is the hex string Fingerprint of the intended signing key. Should be different than the disaster recovery key, preferably specific to the user.|
|**recovery path**|`/media/`|The directory used to determine the mount point or other location of the .tap files expected by the recovery mode./
|**output path**|No Default|The directory to which tapestry is to deliver the final packaged .tap files, and other outputs like the skipped file log or keys exported during --genKey|
|**keysize**|2048|The size of key to generate during --genKey and as part of first time setup. 2048 is the minimum viable, and therefore sane, default.
|**use compression**|True|Toggles the use of Tapestry's built-in bz2 compression handler. If set to true, blocks are compressed before encrypting to keep them under the blocksize.|
|**compression level**|2|A value from 1-9 indicating the number of bz2 compression passes to be used. Experimentation is required for different blocksizes to determine the minimum viable value. 9 passes is maximally efficient, but also takes considerable time, especially on larger blocksizes.|

### Additional Categories
Additionally, the user will find categories for windows and linux options, indicating they are either "default" or "additional" locations for backup. Any number of these definitions can be included at the user's discretion, so long as each option label is unique. When doing this it is desirable to set equivalent paths for both OS varieties, but as Windows support was broken in 0.3.0, the windows categories are not formally significant.

## Runtime Arguments
Tapestry supports the following arguments at runtime:

|argument|function|
|---|---|
|--setup|Drops to the soon-to-be-deprecated setup menu system. The setup menu is badly out of date and crudely designed. It is better to modify config directly using a text editor.|
|--genKey|Generate a new RSA public/private keypair designed to be used as the Disaster Recovery Key. In a pinch this could also be used to generate a signing key, but there are better ways to do that.|
|--inc|Performs an "inclusive run", adding all of the "additional locations" categories to the work list at runtime. Provides non-granular differentation between "quick" and "complete" backups.|
|--rcv|Places the script in recovery mode, checking its recovery path for .tap files and their associated .sigs and recovering them programatically.
|--debug|Increases the verbosity of both Tapestry and its gpg callbacks for light debugging purposes|

If no runtime arguments are provided the program assumes you intended to do a "basic build", and runs the backup routine using only the relevant "default locations" list.

## Key Security
Tapestry relies on a two-asymmetric-key system for its protection, as a mechanism to eliminate the need for trust between the user and their storage solution. Tapestry is currently designed to produce only its own key automatically - for the moment it is taken as read that the user would know how to develop a signing key. Specific instructions for signing key generation can be found in the GnuPG manpage or their online documentation. For the purposes of this section, it will be enough to concern the active and passive key security considerations.

### Disaster Recovery Key versus Signing Key
Tapestry relies on two different keys, hereafter referred to as the Disaster Recovery Key and the Signing Key. It uses these keys for two separate operations: encryption and decryption of the backup files, and signing/signature verification of the same. Seperate keys are used to allow positive identification of the user or terminal (depending on use case) which generated the backup. Signed backups resist tampering in ways that unsigned backups would not - to forge a tapestry backup would require knowledge of the private side of the signing key. Without the signing key, it would be as simple as knowing the public side of the disaster recovery key.

Why use assymetric cryptography at all, when "keyphrase"-based symmetric cryptography would have sufficed? Distribution. 500 systems could comfortably share one disaster recovery key, with each system holding only the public key in its respective keyring, and a trusted admin or other "super-user" in posession of the private side of the key.

### Key Size and Passphrase
By default, Tapestry creates a 2048-bit key when prompted to. This is the smallest common-size key we believe to be reasonably secure. If desired, this figure can be increased, though this is not recommended as it would impact both key generation and overall cryptographic operation time. With cryptography being the second-most computationally-expensive part of the system, and 4096-bit keys being excessive, we have settled on 2048 bit.

All keys use should be protected by a strong passphrase of at least 24 characters.

### Key Storage
Tapestry expects to find the keys it is looking for on the default gnupg keyring, found under `~/.gnupg/`. There is currently no plan in the works to change this.

However, we have some concerns that private keys stored directly in the keyring may not be secure under all circumstances, though we are, of course, professionally paranoid. For the home user, keyring storage is fine. If you are a small business or other organization, it may be preferable to use a smart-card based system. Your existing 2FA solution, such as a Yubikey, may provide this functionality in addition to its normal use. Configuration in this way is beyond the scope of this documentation but highly recommended - the developers have been treating their keys in this manner for some time and find the process highly seamless.

Additionally, it is important to keep a master copy of the disaster recovery key offline and secure at all times as a backup. If you should happen to lose this key, your backups are unrecoverable.

### Passphrase Security
Tapestry Project endorses long passphrases punctuated randomly and including numerals for key passphrases.

Tapestry itself never handles a single passphrase you provide it, either for recovery decryption or signing of backups, or indeed for key generation. This is the reason for the requirement for a recent version of GnuPG to be installed. Tapestry provides the command for the operation to GPG without a passphrase, prompting newer versions of GPG to respond by invoking the pinentry program they are configured to use.

### Other Key Management Considerations
Depending on the nature of your organization it may be desireable to have your Disaster Recovery Key expire - of course, as you are in posession of the master key, you can extend these expiries indefinitely. An expired card cannot be used to encrypt new messages, but it can still be used to decrypt messages sent to it.

A similar principal of operation exists for revocation certificates. At present, it is not programatically possible for Tapestry to neatly generate a revocation certificate - you should perform this operation yourself as soon as a new key is generated and again, store it as securely as possible. In the event your private key becomes compromised, you can issue the revocation certificate by pushing it to any and all keyservers you are using, which prevents new backups being created which would be decodable by that key.

While we encourage keeping a copy of the master DR key's private side offsite in case of catastrophe, we do not encourage using online services to do so.

For home users it may be excessive, but as an organization I highly recommend generating keys on an offline machine, perhaps even from a known-clean live boot environment.

## Selecting your "Locations"
Tapestry treats every location defined in its configuration file as the top of an os.walk() command. This means, in practical terms, that everything in every subdirectory of that location will be backed up. Therefore, it is important to consider if any symbolic links are going to be followed that may end up with unintended consequences.

The specific locations you select are entirely up to you. At time of writing I personally use the documents and photos default folders in my default locations list, with my additional locations list including videos, music, and a subset of the hidden configuration directories.

## Example Runsheet: First-Time Setup
0. Download the latest version of tapestry from the github repo (at time of writing, 0.3.1), and verify it against its own signature. To do this you will need a copy of [this key](https://pgp.mit.edu/pks/lookup?op=vindex&search=0xF373FF4B43FC742F).
1. Unpack the verified tar of Tapestry. It should contain Tapestry.py, README.md, DOCUMENTATION.md (versions 1.0 and up), and an example tapestry.cfg file.
2. Open up tapestry.cfg in your text editor of choice and adjust the configuration as follows:
 - Refer to the configuration table above for explanations of the environment variables, and;
 - Define default and additional locations as required by your backup model.
3. Run tapestry.py using the standard methods for invoking a python script, with the `--genKey` flag. This will be a command similar to:
```
python3 tapestry.py --genKey --inc
```
4. Follow the onscreen directions to generate your first disaster-recovery key.
5. (Optional) Take the time now to generate a signing key if you don't already have one, as well as the revocation certificates for both. Be sure to back these up and store them securely.
6. Store your keyfiles and the generated inclusive backup safely and securely.
