# Documentation for `positive_tests.py`
Tapestry/Testing's positive-control unit test suite is implemented in `positive_tests.py`, which contains a runtime function to handle the actual execution of tests, and all the tests to be covered in this scheme as individual functions. `positive_tests.py` is not intended to be run independaently and should be invoked by sitting within the `Tapestry/Testing` directory and invoking `python -m tests` (as appropriate) - it requires information provided by this execution method in order to function.

These positive test suite should contain any and all tests which validate that a function or class method behaves in the intended manner when provided a valid input.

## Modifying `positive-tests.py`
Owing to the way positive-tests.py is meant to be invoked, adding new tests is both simple and slightly involved, in that it's slightly more steps than simply creating a new function. The following workflow is suggested.

 1. Define the new test as a method in the appropriate alphabetical order among the other `test_sometest` functions toward the bottom of the file.
 2. Add the function by its name (without arguments or a call paren `()`) to either `list_local_tests` or `list_network_tests` as appropriate.
 3. Add an entry to `Testing/Resources/config/positive_tests.json` in the following format, using your test's function name as the key. (omit the outermost pair of `{}`, required to satify formatting requirements):
 ```JSON
 {
   "test_verify_invalid_block": {
        "title": "------------------[Block Signature Validation Test]------------------",
        "description": "This test validates that tapestry will reject a file with invalid signatures",
        "pass message": "[PASS] The verify_blocks correctly ignored the invalidly-signed file.",
        "fail message": "[FAIL] See Error:"
    }
}
```

As a note, it is perfectly acceptable depending on the test logic for either `"pass message"` or `"fail message"` to reference empty strings. This can be done if, for example, multiple responses are expected from a single test even in the event it passes.

These test functions are being called by `test_case`, a function found in the `framework.py` file (see FRAMEWORK.md). From a development perspective, this has the following implications:
- The only argument a test receives is `dict_config`, which is a dictonary of information parsed out of `test_config.cfg`. If you need to add new information to this file you will have to amend `tests/__main__.py` to make sure it's passed, and add the relevant key to the `expects` list near the beginning of `positive_tests.runtime`.
- The logic of test_case expects an array to be returned, and:
    - if `len(0)`, test_case will log the pass string, else
    - if any other length, test case will log the failure string, then write each item in the array into the log as well. This is so that the returned array can be used to raise specific errors, to provide more information to the developer about possible causes of failure.
- Some tests work around the array return logic by not providing a str_pass or str_fail arugment and instead using the array itself to provide lines to write into the log. A good example of this is `positive_tests.test_build_ops_list` which includes neither as it is actually a series of nested tests, all acting upon a single function.

### Requirements/Targets for New Tests
In order for new tests to be accepted fully into positive_tests.py, they should:
- Satisfy the requirement of demonstrating that a given tapestry method or function behaves as expected under standard inputs.
- Be PEP-8 Compliant, as with any submission into the Tapestry codebase.
- Handle any unexpected returns (including raised exceptions) in an elegant way.
- To the greatest possible extent, operate without reliance on previous tests or files-on-disk:
 - If a file from the disk is required, it should be clearly noted in the docstring for the new test and the file itself should be included in the commit that adds the requirement.
 - If a previous test really is a dependancy, the failure messages for the test(s) which come after should indicate this. For example, if test_foobaz requires test_foo to have completed successfully, a failure message such as `[FAIL] test_foobaz raised a NameError. Did test_foo fail too?`
- The catalog entry in `positive_tests.json` should be broadly conformant with the existing entries in that:
 - Title should be a `width=79` string, with the title in square brackets `[]` and hyphens `-` used to pad the width of the line.
 - Description should be sufficiently descriptive as to have a basic understanding of what the test did and why. Need not be as verbose as the docstring for the test itself.
- Any tests added after the `test-enahnce` branch should include a `try except` catch looking for `AttributeError`, wrapped around the actual call into Tapestry. This is so that the absense of a function having been defined will cause the test to fail rather than crash the whole test suite.
 
## Documentation of Individual Tests
Due to the requirement that all tests be PEP-8 compliant and include a docstring, it's more useful to refer directly to `positive-tests.py` for usage information regarding each test, and technical documentation on the code itself. As the tests were never intended to be called independently, this document contains *explanations of test logic* rather than calls. All tests accept only one argument, after all.

- **test_block_meta** - A test to validate that `tapestry.Block.meta()` behaves as expected, by generating and placing an RIFF file in a known path. We use this RIFF file in some later tests.
- **test_block_valid_put** - provides a synthetic `findex` object to a synthetic `tapestry.Block` object via the `put()` method. Both objects are calculated so that the put should succeed - the test fails if the response from `put()` matches the behaviour case that the file was rejected.
- **test_block_yield_full** - creates a synthetic Block object, then uses put() to take up the remaining space, and checks the value of `Block.full` - if true, the test passes.
- **test_build_ops_list** - calls build_ops_list twice against part of the overall file structure and validates a number of points. If any of these sub-tests fail, an overall fail is reported for this test:
 - Inclusive vs Exclusive (corresponding to Tapestry's `--inc` flag) behaves as expected
 - Do the file counts for both runs match what the test itself counted?
 - For each object in the ops list, are the appropriate keys/attributes present (this function returns a list of dictionaries describing individual files)
 - Do the sizes indicated in the response line up with what is observed on disk directly?
 - Do the file hashes reported in the response line up with what is observed on disk directly?
- **test_build_recovery_index** - A synthetic example of the response from `tapestry.build_ops_list` is provided to `tapestry.build_recovery_index` and the test validates if the return indicates a list of fileIDs in the expected order, and an accurate sum of indicated file size.
- **test_media_retrieve_files** - Points `tapestry.media_retrieve_files` at a location where we expect a valid .tap and .tap.sig file to exist, and determines if MRF correctly returns a RecoveryIndex object when executed in this condition. Contains some error logic for if those test articles are missing.
- **test_parse_config** - Pulls up `control-config.cfg` from the test articles directory using `tapestry.parse_config` and examines the namespace object which was returned to ensure that the expected values are all returned.
- **test_pkl_find** - creates a `tapestry.RecoveryIndex` object using a static test article of the old (pre v2.0) `pickle`-based recovery index format, then attempts to find a file it is known to contain. This is essential as reverse-compatibility as far back as v.0.3.0 is desired.
- **test_riff_compliant** - opens the test RIFF generated by `test_block_meta` and ensures that the file is fully compliant in structure with the current published standard for RIFF (see main documentation or the Tapestry wiki on github.)
- **test_riff_find** - creates a `tapestry.RecoveryIndex` object using a static, known-good file in the newRIFF format, then tries to find an entry it is known to contain.
- **test_TaskCheckIntegrity_call** - creates a dummy file of a random (but known to the test) content, and takes a control hash from it. Provides the file path and control hash to an instance of `tapestry.TaskCheckIntegrity`, which it then calls.
- **test_TaskCompress** - attempts minimal compression-in-place of a small file. Validates if the file passed. Content validation is handled in the next test.
- **test_TaskDecompress** - decompresses the file compressed by `test_TaskCompress`, then checks the hash of the decompressed contents against the hash of the original contents to ensure no changes were made.
- **test_TaskDecrypt** - Decrypts a file encrypted during TaskEncrypt and checks the contents to ensure that they were not changed in the process.
- **test_TaskEncrypt** - Attempts to generate the test file used in `test_taskDecrypt` by calling TaskEncrypt around a file known to exist.
- **test_TaskSign** - Signs a file using a fixed key. If the signature operation fails, so does the test.
- **test_TaskTarBuild** - As `test_TaskCompress`, but for tarring rather than compression.
- **test_TaskTarUnpack** - Unpacks that which was created by test_TaskTarBuild by calling the appropriate task class out of tapestry, then validates the contents using a checksum.
- **test_verify_blocks** - Uses the testing bypass to check that a tapestry block with a known-good signiature file would pass verify_blocks, without waiting for human interaction at the appropriate place.