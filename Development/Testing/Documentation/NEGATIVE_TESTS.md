# Documentation for `negative_tests.py`
Tapestry/Testing's negative-control unit test suite is implemented in `negative_tests.py`, which contains a runtime function to handle the actual execution of tests, and all the tests to be covered in this scheme as individual functions. `negative_tests.py` is not intended to be run independently and should be invoked by sitting within the `Tapestry/Testing` directory and invoking `python -m tests` (as appropriate) - it requires information provided by this execution method in order to function.

These negative test suite should contain any and all tests which validate that a function or class method behaves in a sane method when unexpected or invalid inputs are given. This includes both tests to ensure expected-failure scenarios behave as expected, and tests which avoid regressions in issues since closed.

## Modifying `negative_tests.py`
Owing to the way negative_tests.py is meant to be invoked, adding new tests is both simple and slightly involved, in that it's slightly more steps than simply creating a new function. The following workflow is suggested.

 1. Define the new test as a method in the appropriate alphabetical order among the other `test_sometest` functions toward the bottom of the file.
 2. Add the function by its name (without arguments or a call paren `()`) to either `list_local_tests` or `list_network_tests` as appropriate.
 3. Add an entry to `Testing/Resources/config/negative_tests.json` in the following format, using your test's function name as the key. (omit the outermost pair of `{}`, required to satify formatting requirements):
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
- Satisfy the requirement of demonstrating that a given tapestry method or function behaves sanely when an unexpected or invalid input is given.
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
Due to the requirement that all tests be PEP-8 compliant and include a docstring, it's more useful to refer directly to `negative_tests.py` for usage information regarding each test, and technical documentation on the code itself. As the tests were never intended to be called independently, this document contains *explanations of test logic* rather than calls. All tests accept only one argument, after all.

-**test_block_invalid_put** - Attempts to place a synthetic `findex` object into a block for which it is too large using `put`
-**test_decompress_uncompressed** - calls an instance of `tapestry.TaskDecompress` against a non-bz2-compressed file, for which it is expected to return a response indicating the file was skipped.
- **test_recovery_index_invalid** - calls an instance of RecoveryIndex against an invalid file to ensure the correct exception is raised.
- **test_verify_invalid_block** - calls verify_blocks into a directory where a block with a deliberately-broken signiature exists and fails the test if any more than the one expected good file is accepted.
- **test_sftp_connect_invalid** - Tests the SFTP connection function will not connect to servers other than the one with an explicitly-provided-trust in the config.
- **test_sftp_connect_down** - Tests that the SFTP connection behaves in a predictable way when the SFTP server cannot be found, as a local-storage failover would be needed in such a case.
- **test_sftp_place** - Validates a predictable failure mode when the sftp_place function tries to put a file somewhere it is not permitted to do so, as a local-storage failover would be needed in such a case.
- **test_sftp_find** - What happens when we try to run find in a location that doesn't exist?
- **test_sftp_fetch** - What happens when we try to retrieve a file that doesn't exist or for which we don't have permission? This shouldn't be possible based on how the fetch function is called, but you never know.