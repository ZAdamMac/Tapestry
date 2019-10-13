# Tapestry Testing Methodology
As you might have noticed, the test framework for Tapestry is a little... idiosyncratic. The tests needed to be portable and accessible across a number of platforms and at a rather low barrier to entry, both in terms of writing the tests themselves into the system, and in terms of actually calling on and executing those tests.

The test-enhance branch, which was merged between Tapestery v2.0.1 and v2.0.2, entirely changed the testing methodology away from a functional-test focus and into faster-iterating, unit-test-focused coverage. This change was made possible by the v2.0 rewrite, which focused the overall structure of Tapestry on Return Oriented Programming.

## Unit Tests for Commits
While it is by no means mandatory for contributors, a personal goal was to rebuild the test coverage in souch a way that a fairly broad swath of Tapestry can be tested using unit tests, contained in `positive-tests.py` and `negative-tests.py`. This allows for a much faster testing process, with a general assurance that if the returns are operating as expected (as asserted in the tests), the actual runtime tests prior to release are more likely to pass. The overall goal there is to allow for tests to be sufficiently sprightly to run them at each commit, verify that the results are as-expected, and then have less debugging work to do prior to the merge of the working branch back into master. A lack of this sort of responsiveness was a major headache in the `2.0` release structure and nearly killed the project.

Tapestry/Testing's unit test components consist of two broad swathes of tests:
- `positive-tests.py`, consisting of Positive Control tests which validate that, for a known-good input, the function or method under test returns the exact output expected.
- `negative-tests.py`, consisting of Negative Control tests which validate that the methods and functions under test fail in the expected way when otherwise invalid inputs are given. This is both critical for making crashes predictable/avoidable and as a general security and reliability measure.

Strictly speaking, the unit tests don't rely on a full test corpus, though a few of them ingest either local configuration files or local test articles which are all stored in the repo itself. The overall unit test phase typically completes in a few seconds, making it appropriate as a pre-commit action.

## Functional/Integration Testing for Merges
When the rubber hits the road, it doesn't matter if every single unit test passes if the program itself doesn't run in the expected way. To facilitate that, the tests can also be called with a given `--runtime` flag, triggering the test set to include the runtime tests.

These tests call *the version of tapestry currently installed in the environment* to perform their functions, and run it in each of its `--genKey`, `--inc`, and `--rcv` modes, then uses a simple hash-based integrity check to make sure that the output of the three runs did not change any of the files in the original test corpus.

While further instructions are included in `TESTING.md`, broadly speaking the Runtime Tests do require the existence of a test corpus, which can be managed with `corpusmaker.py`.

## Reproducibility of Testing Results
With the exact process covered in more depth in `TESTING.md`, there is an assumption made that the version of tapestry involved in your environment is the same version stored at `Development/Source/Tapestry` locally. This requires a process of iterative packaging and installation for testing, but allows the test output logs to contain a record of the SHA256 hash of both the `Tapestry/__main__.py` and `Tapestry/classes.py` files.

This methodology allows for two things:
- A user can validate that the source code they were using was tested by the Dev Team by comparing the relevant logs in `master` with the file hashes for the version of Tapestry they have available, and
- Dev Team can validate quite quickly whether the code being committed is the same code that was previously tested, allowing us to decide if we trust it sufficiently to run the tests ourselves locally.

Since the `CONTRIBUTING.md` policy requires incoming PRs to include these test logs, and the code and tests are readily available, Dev Team can very quickly reproduce the test results before deciding whether or not to merge incoming PRs to master or package a release.