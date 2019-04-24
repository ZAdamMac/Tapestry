# Testing Documentation for Tapestry Project
## Current for releases 2.1 and later

This document is intended to lay out a brief explanation of the correct use of the provided scripts in testing Tapestry, for use in development. A two-tiered testing model is in place, with unit testing coverage for "feature merges" and functional, runtime testing for "release merge".

## Feature Merging
Moving forward, work toward a given new feature should comprise *it's own branch*, preferably forked from whatever the latest state of `release-dev` was current at the time. #####

Testing a feature merge prior to merging is a requirement. Ideally these tests would be run by the person submitting the PR. The person responsible for review would then run the tests again as a formality to verify the results - if possible, this latter step of testing should be automated where possible.

This stage of testing relies on the Tapestry Unit Tests suite to perform on-the-fly unit tests of all known parts of Tapestry.

### New Feature Testing
*"The difference between science and screwing around is writing it down!"
-- Adam Savage*

While some cosmetic changes, bug fixes, and other "features" will be covered by the existing tests, some new features will introduce entirely new classes, methods, and functions into Tapestry. When this is the case, the necessary new tests should also be created and submitted as part of the relevant PR. The person supervising review should then take the new test code, review it, and if satisfied it is a suitable test, the new tests will be incorporated along with the new features when the PR is merged.

It is important to note that any new function requires at least two new tests - a positive test showing that the object functions as designed when supplied with nominal inputs, and one or more negative controls which both prove the object will fail when it is supposed to AND fails gracefully in a manner that is consistent with good error handling practices.

Please make sure any new tests are clearly documented and that their output is meaningful and consistent with the general style of the existing test suite.

### Unit Tests Design Philosophy
*Full Documentation of the Unit Tests can be found in docstring format within the tests themselves. This section discusses the general philosophy of the unit test design.*

In general, there are three aims to this level of testing:
1. Provide the greatest assurance possible that Tapestry would continue to pass functional testing;
2. Provide the greatest assurance possible that Tapestry's design remains as secure as is reasonably possible given its dependencies, and;
3. Do so in a manner that is both reproduceable and, as near as possible, stateless.

Ideally the tests should be written and constructed in such a way that their output is clear, clean, and standardized. In cases where a test could have multiple failure conditions, those failure conditions should be expressed in such a way as to distinguish between them. Further, the docstring of a given test should provide enough insight into the test's purpose to aid in divining what a failure of that test should mean. Finally, errors in test cases *must* be caught. Failing to catch exceptions in testing will result in a crash of the test suite itself which is not an ideal situation.

In keeping with number 3, no file should be relied upon in the testing that is not either committed as part of the test suite or, perhaps more ideally, expressed as a string in the tests themselves. This is to facilitate containerization of the tests for future automation/quality of life improvements.

## Release Merges
The release merge is the big day, the moment we've all been waiting for - the merge of `release-dev` into `master`, signifying the immanent release of a feature update! However, because unit tests are not the end-all-be-all, and because Tapestry has official support for both Linux and Windows systems (with implied support for MacOS), we need to do some additional testing to make sure everything works well.

### Runtime Tests
The runtime tests have been redesigned since 2.1, and so has the testing criteria. The need for a massive, 10+ GB test corpus is obviated. Unit testing can provide the assurances formerly provided by the large corpus, allowing for additional runtime tests to be performed.

Much like was the case with the unit tests, specific documentation for the runtime tests can be found in the tests themselves. From a high-level, the general rule is that anything tapestry can be told to do should be tested as a functional test - any flag, really, apart from `--debug` and `--devtest` should be argued.