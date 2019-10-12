# Using the Tapestry Testing Framework

Use of the Tapestry Testing Framework is not yet quite a fully-automated process, executable with a keyboard shortcut prior to commit. There's still no CI framework in place, either.

Right now, the general path of testing Tapestry under TTF looks something like this:
0. Create a virtual environment to isolate your test version of tapestry from broad (optional but highly recommended)
1. Package the current version of tapestry you're developing.
2. Install Tapestry from this local package
3. Run the tests

The Python Documentation has [better information on using virtual environments than we could ever hope to produce.](https://docs.python.org/3/tutorial/venv.html)

# 1. Packaging Tapestry
Much like the Development Team would do in order to get ready to push a new version of Tapestry to PyPI, the source of the development version of tapestry can be packaged quite nicely. From a shell located at `Tapestry/Development/Source`, run:

```commandline
python setup.py sdist
```

Using your appropriate python callable.

This will generate a large number of additional files which you do not need to add to vcs - in point of fact if you commit the build, wheel, and egg files into your PR it will be rejected.

# 2. Installing Tapestry from the Test Environment
While within your test environment, you can install the test version of tapestry to that environment using the following command:

```commandline
pip install --editable .
```

This will install tapestry in the Virtual Environment, and do so in such a way that your edits to the source will be instantly reflected.

# 3. Run the Tests
Depending on your needs, the tests support a few options.

While operating in your virtual environment, you can change directory to `Tapestry/Development/Testing` and invoke the tests this way:

```commandline
python -m tests
```

There are effectively three testing modes to choose from:
1. By default, only the suites in positive_tests.py and negative_tests.py will be run. This is the fastest method and usually completes in no more than a handful of seconds, and is ideal for pre-commit testing of small changes.
2. If you're testing for network functionality I recommend supplying the flag `--network`. This will trigger any network-related unit tests in the positive and negative control sets. Before doing so, you should make sure you have the appropriate network targets (such as SFTP servers, etc) up and running.
3. If the commit you're about to test will be submitted as part of a PR, it's mandatory to first run all tests, so supply both `--network` and `--runtime` as flags.