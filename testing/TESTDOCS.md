# Testing Documentation for Tapestry Project
## Current as of release 1.0.0

This document is intended to lay out a brief explanation of the correct use of `functional-tests.py` in testing Tapestry for use in development. **No fork may be pushed to Master until its version of dev.py passes all tests.** Functional Testing is the current best-fit method for testing Tapestry in a reproducible way during development and will likely remain such until the 2.0 rewrite.

## Preparing the Test Environment and tapestry-test.cfg
`funtional-tests.py` relies on a testing environment to run its target script against. That environment can be constructed relatively simply using the included `corpusmaker.py`. The method of preparing this environment is simple:

1. Create some directory `~/Tapestry Testbed/` on your testing machine's filesystem.
2. Under this functional root, create `/Control` and `/Test/`.
3. Edit `corpusmaker.py` such that its `dest` global variable points at some sub-directory Corpus, ie `~/Tapestry Testbed/Control/Corpus`.
4. Run corpusmaker. Depending on your system specifications this operation may take up to an hour to complete - you are generating a considerable amount of data after all.
5. After running corpusmaker, you must configure the `tapestry-test.cfg`. This is simply a version of an ordinary tapestry config file. If you downloaded the test.cfg file from the repo, simply edit its paths so that they point at your test envrionment instead of some guy named Patches'.
6. Create the following known-good samples: `Non-Inc Media` and `Inc-Media`, consisting of the output .tap and .tap.sig files of an inclusive and non-inclusive run respectively. These are used in some tests. You should also manually unpack the recovery-pkl file from one of these and leave it under the `~/Control` as some tests require it.

## Testing a Development Build
In order to test some variation of `dev.py`, simply copy it into the testing directory locally and run functionaltests.py. Testing can take a considerable amount of time, during the early stages of which the developer will need to be semi-present. A future version may obviate these requirements. In particular, the following sequences will require user intervention:

- Immediately upon running, when the script is testing `--genKey`, the developer will need to provide credentials for the key to be generated as though they were a user. Of particular note: the password will need to be provided twice, once during creation and once when the keys are exported.
- During the `--genKey` run, Tapestry will perform a non-inclusive run, as normal. Toward the end of this run the developer will have to supply the password a third time to execute a signing operation.
- After finishing the first run, Tapestry will then begin an inclusive run. The user must assent to using the key provided (a press-any-key moment) if not deprecated. The run will then proceed as normal until the user provides a password for singing.
- In some circumstances the user may have to intervene during the third, recovery run, if the signatures fail to match correctly, and provide the corresponding key to unpack. All of these interruptions come at the beginning of the recovery process.
- From there on out, the user may allow the testing script to complete its run as normal. The system will run all of its tests and report their results to both STDOUT and a logfile stored under `~/Test`

## Technical Details of Tests
### Identity Tests
The first test run is an Identity Test, comparing the output version of the corpus to the known-good control corpus. Dictionaries are created listing every file in the control and test corpuses as key, with value being the md5 hash of the file. A simple comparison is then run and any deviations are logged.

If there are no deviations, the test passes - the implication is that the backup was successfully restored. If any differences are observed, the test fails. Technically, it would be possible to use this test alone, but that is insufficiently granular.

### Cryptographic Tests
#### Decryption of .tap file
The testing script attempts to decrypt a .tap file and reports success or failure. This is done in the event of a failure of the identity test to rule out an encryption error being the cause of the failure. As Identity cannot pass without decryption succeeding, this is all that is necessary.

#### Signature Verification
The script verifies the signature of a .tap file and reports success or failure. This is run regardless of the failure or success of other tests owing to the criticality of the signature function.

### Version Specificity/Backward Compatibility
If Identity fails, the testing script will fetch the recovery-pkl file from one of the test .tap blocks, and compare it to a known-good recovery-pkl sample. If the two files are different signficantly (other than list orders), the test will fail, with the observed differences logged.

Changes to expected recovery-pkl files are the largest cause of backward-forward compatibility breaking between versions.

### Compression Tests
The testing script makes a few tests involving file size, collectively referred to as compression tests.

#### Inclusivity Test
The testing script has generated both inclusive and exclusive sets of .tap files. This test simply compares the size of the two. It passes if the inclusive set is larger, and fails otherwise. If the test has been run against the control corpus output by corpusmaker.py, this is sufficient to demonstrate that the different sets of control lists are being handled correctly.

#### Blocksize Compression Test
The testing script compares the size of all of its output blocks (the .tap files) to the blocksize defined in `tapestry-test.cfg`. If none exceed, the test passes.

#### Random Noise Failure Test
In the event that the Blocksize Compression Test fails, a special test is run where a .tap file is decrypted, and decompressed. The decrypted version is compared in size to the decompressed version. If the decrypted version is in fact larger than the decompressed version, this test fails.

The failure of this test indicates that the test corpus data was insufficiently structured to compress properly. It's a special case test to deal with a mode of failure encountered during the design of 0.3.0.

### Export Test
The testing script looks for, and attempts to import, DR.key and DRpub.key. If either fail, the corresponding test also fails.

## What about $some_feature?
### Extant Features
Some extant features of Tapestry are not explicitly tested for. In most cases, their tests are implicit:
- If Identity succeeds it didn't matter what the Blocksize value was set to.
- Nothing from init() or setup() is tested as both scripts are to be deprecated in the near future.
- "Bad Return" feature is implicitly tested for by the way in which the testing script runs the final recovery pass - if it is not working, Identity would fail.

### New Features
If your PR/development arc includes adding new functionality to the program that is not explicitly tested for, contact `tapestry@psavlabs.com` to discuss adding a test. It may be possible to construct your own under most circumstances.

## My Tests Passed!
Congratulations! Please include the passed output `test-$somedate.log` in your PR for public review.

*"The difference between science and screwing around is writing it down!"
-- Adam Savage*