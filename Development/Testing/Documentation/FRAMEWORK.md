# Documentation for `framework.py`
Tapestry/Testing's principal helper file is `framework.py`, which contains a small number of functions used in common across some or all of the actual test packages. This method should be preferred over copy/paste implementation for refactor-resistance an as a generally safe coding practice.

## Modifying `framework.py`
If for some reason you were preparing a large number of new unit tests that all required common functionality, it may be desirable to break out some of that functionality into a helper object of some type and added it to `framework.py`.

This of course can be done - simply adding classes and functions to this script won't produce any changes as it is purely definitional.

Of course, if `framework.py` were to be modified by the deletion or refactoring of a class, method, or function, that refactoring work would have to be completed across all test packages or something most certainly *would* break.

## Classes of the Framework
Framework currently exposes a single class, SimpleLogger.

### SimpleLogger
The SimpleLogger class is an inheritor of python's `(object)` built-in class, and exposes a few convenience methods. While not a true logger integration or particularly intelligent (there is, for example, no concept of severity level), SimpleLogger more than suffices to create new test log files, adding the appropriate header and footer at the appropriate time, and registering new lines into the file.

SimpleLogger exposes the following methods:

#### framework.SimpleLogger.__init__(landingdir, name, test):
Accepts landingdir as a string expressing a path (ideally absolute) to place the output file, which will be titled by the name argument (also a string). The "test" variable is a string as well, and should correspond to the filename of the test file calling the logger, without the file extension.

In addition to creating the file where requested, this method creates a standard-format header at the top of the logfile which includes a short explanation of what is happening, as well as some basic information about the system running the test: the number of processor cores exposed to python at the time, and the amount of RAM on the system as a whole, both according to utilities exposed in the `os` standard library module. This information is included as a very crude benchmark, which can be relevant when comparing execution times.

#### framework.SimpleLogger.log(message):
Accepts message, a string, which is written to the log. A newline `\n` is appended to the end of message for formatting reasons.

While future work may make this method wrap intelligently, it is not seen as necessary as that wrapping is already handled by `framework.test_case`

#### framework.SimpleLogger.save():
A convenience method that writes a footer leaving the date and space for tester comments (to be added after the fact), then closes the file handle which was opened when the SimpleLogger was initiated.

### Functions of the Framework
At present, framework exposes three functions which can be used by various tests in the test suite.

#### framework.elapsed(start):
This simplistic function accepts a time object, such as that produced by a prior call of `time.monoclonic()`, and compares it against a fresh `time.monoclonic()` call result, returning a string of the format "HH:mm:ss" for the resulting time difference.

**Usage**: The intended use case of this function is to assign start prior to running some test, then to call elapsed to get the amount of system time elapsed during the execution of the test itself. This introduces error exactly equal to twice the delay introduced by the global interpreter lock, but on a modern system this is sufficiently negligible as to be excluded, since we're only returning a time to the nearest second anyway.

#### framework.test_case(config, logger, test, str_title, str_head, str_pass, str_fail)
Allows the execution of some manner of test logic while wrapping all the logger operations in a single call. This method allows a maximization of code reuse for the tests.

The test function needs to accept only the dict_config object being used in the test suite for its arguments and must return a list of error responses to be printed. test_case will write those responses somewhat intelligently into the log file by wrapping them at 79 characters in line width.

- config: a dict_config object as provided to the test suite. This object is actually created during execution of `tests/__main__.py` and then handed to each test suite as it runs.
- logger: an instance of SimpleLogger, whose `log` method will be called iteratively throughout execution of the function.
- test: the variable assigned to a given test function, rather than a call of the function itself (that is, expressed without any arguments or an empty paren `()`). This is the test to be called in this test case.
- str_title: a string to use as the title of the test in the test log.
- str_header: a string to use as a header for the test - by standard, this is a description of the test, sometimes with commentary on the test logic itself.
- str_pass: a string to be added to the log in the event that `test` returns an empty array, indicating absolute passage.
- str_fail: a string to be added to the log prior to the results of `test` in the event a test fails.

#### framework.validate_dict_config(config, expected):
Validate that everything needed in these tests is present in the config dictionary provided by main. This should be updated if any new parameters are needed. Each test suite needs to test for its own set of valid values.
- config: the dict_config dictionary passed into the test suite by `__main__` after parsing test_config.cfg
- expected: a list of keys which the suite expects to find in `config`.

This function simply returns `True` if there are no keys in expected which cannot be found in config.