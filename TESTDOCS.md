# Testing Documentation for Tapestry Project
## Current as of release 2.0

This document is intended to lay out a brief explanation of the correct use of the provided scripts in testing Tapestry, for use in development. **No fork or branch may be pushed to Master until its version of dev.py passes all tests.** Primary coverage is to be provided by unit testing of individual functions or rountine-functions, with Functional Testing to provide assurance the whole program functions as intended. Going forward, new features should be added in such a way that they are unit-testable whenever possible.

## Preparing the Test Environment and tapestry-test.cfg
The test suite relies on a testing environment to run its target script against. That environment can be constructed relatively simply using the included `corpusmaker.py`. The method of preparing this environment is simple:

1. Create some directory `~/Tapestry FT Data/` on your testing machine's filesystem.
2. Under this functional root, create `/Control` and `/Test`.
3. Edit `corpusmaker.py` such that its `dest` global variable points at some sub-directory Corpus, ie `~/Tapestry FT Data/Control/Corpus`.
4. Run corpusmaker. Depending on your system specifications this operation may take up to an hour to complete - you are generating a considerable amount of data after all.
5. After running corpusmaker, you must configure the `tapestry-test.cfg`. This is simply a version of an ordinary tapestry config file. If you downloaded the test.cfg file from the repo, simply edit its paths so that they point at your test environment instead of some guy named Patches.
6. Create the following known-good samples: `Non-Inc Media` and `Inc-Media`, consisting of the output .tap and .tap.sig files of an inclusive and non-inclusive run respectively. These are used in some tests. You should also manually unpack the recovery-pkl file from one of these and leave it under the `~/Control` as some tests require it.
7. If it is not already present, install vsftpd. vsftpd will be automatically invoked by the test framework itself; if desired, the developer may choose to disable vsftpd as a startup script. A dummy account should be created for ftp testing purposes so as not to interfere with the normal operation of users on the account (and allow account whitelisting for the security-conscious.)

## Testing a Development Build
In order to test some variation of `dev.py`, simply copy it into the testing directory locally, start two copies of vsftpd (one for each config) and run `runtime-tests.py` followed by the remaining test scripts in any order. The vsftpd daemons must be run seperately in order as running as superuser is required. Testing can take a considerable amount of time, during the early stages of which the developer will need to be semi-present. A future version may obviate these requirements. In particular, the following sequences will require user intervention:

- Immediately upon running, when the script is testing `--genKey`, the developer will need to provide credentials for the key to be generated as though they were a user. Of particular note: the password will need to be provided twice, once during creation and once when the keys are exported. Blank passwords are allowed.
- During the `--genKey` run, Tapestry will perform a non-inclusive run, as normal. Toward the end of this run the developer will have to supply the password a third time to execute a signing operation, if using a password-protected signing key for testing.
- After finishing the first run, Tapestry will then begin an inclusive run. The user must assent to using the key provided (a press-any-key moment) if not deprecated. The run will then proceed as normal until the user provides a password for singing.
- In some circumstances the user may have to intervene during the third, recovery run, if the signatures fail to match correctly, and provide the corresponding key to unpack. All of these interruptions come at the beginning of the recovery process.
- From there on out, the user may allow the testing script to complete its run as normal. The system will run all of its tests and report their results to both STDOUT and a logfile stored under `~/Test`

## Technical Details of Integrity Tests
While the bulk of testing before focused on integrity tests applied to the corpus produced by the functional test, a few remain which are done in this way after Tapestry 2.0. 

### Identity Tests
The first test run in `integrity-tests` is an Identity Test, comparing the output version of the corpus to the known-good control corpus. Dictionaries are created listing every file in the control and test corpuses as key, with value being the md5 hash of the file. A simple comparison is then run and any deviations are logged.

If there are no deviations, the test passes - the implication is that the backup was successfully restored. If any differences are observed, the test fails. Technically, it would be possible to use this test alone, but that is insufficiently granular.

### Blocksize Compression Test
The testing script compares the size of all of its output blocks (the .tap files) to the blocksize defined in `tapestry-test.cfg`. If none exceed, the test passes.

### Export Test
The testing script looks for, and attempts to import, DR.key and DRpub.key. If either fail, the corresponding test also fails.

## Unit Tests
In these tests, specific functions are imported from dev.py and their operation tested against known-good values.

### Cryptographic Tests
All cryptographic tests rely on known keys for stability reasons. These keys are included in the Testing package as "test_crypto.key" and "test_sign.key" respectively. If you choose to use different keys you will have to update the corresponding namespace variables in `establish_namespace()` of `unit-tests.py`.

#### Encryption Test
A paintext value is passed to the encryption function (together with a test flag) to compare the expected output with a known-correctly-encrypted value.

#### Decryption Test
This test leverages the decrypt-block function to decrypt a "sample" tapfile. A flag is passed to bypass some of the heavier file operations and instead the plain and encrypted values of two strings are compared.

#### Signature Verification
The script verifies the signature of a .tap file and reports success or failure. This is run regardless of the failure or success of other tests owing to the criticality of the signature function.

Additionally, this test is run again against a known-bad dataset to ensure it captures, after a flaw was discovered in Tapestry 1.0.1.

### Version Specificity/Backward Compatibility
There are two tests which provide for an assurance of backward-compatibility under Tapestry: the config-comparitor and the NewRIFF Strucutral Test.

#### Config Comparison
The configuration comparison test must be rewritten with each release. This test is simple - it looks to see that every value which should be found in the configuration actually is. This test is necessary because a standard practice is to update .dev without overwriting the config file. Future versions should include code to catch exceptions when an expected config value is absent (and define sane defaults.)

#### NewRIFF Structural Test
Updated each development cycle, the NewRIFF structural test compares the value of an extracted RIFF from the test packages generated by `functional-test.py`. It then uses a hard-coded list of expected key values and seeks to make sure that all values found in the RIFF in old versions are still found in new versions. It will also alert if a new RIFF value is detected with a `[WARNING]` message.


### Inclusivity Test
The script captures the return of the buildRunList() test twice, passing in different arguments each time to produce an inclusive and non-inclusive return. If the values match their expected values, the test will pass.

### Networking Tests
#### Certificate Validity Tests
Two tests run sequentially which first ensure Tapestry will reject an invalid certificate and accept a valid one.


#### File Transfer Tests
Back-and-forth tests, with hash comparison to make sure the files are unaltered in the process. Quite simple. A hash is taken of a sample file, which is then transferred to a "remote" server, and retrieved from it. The hashes of the original and received copies are compared and any deviations reported as failures.


## What about $some_feature?
### Extant Features
Some extant features of Tapestry are not explicitly tested for. In most cases, their tests are implicit:
- If Identity succeeds it didn't matter what the Blocksize value was set to.
- "Bad Return" feature is implicitly tested for by the way in which the testing script runs the final recovery pass - if it is not working, Identity would fail.

### New Features
If your PR/development arc includes adding new functionality to the program that is not explicitly tested for, contact `tapestry@psavlabs.com` to discuss adding a test. It may be possible to construct your own under most circumstances.

## My Tests Passed!
Congratulations! Please include the passed output logs in your PR for public review. It is appreciated if you could sign your code and the test logs as well.

*"The difference between science and screwing around is writing it down!"
-- Adam Savage*