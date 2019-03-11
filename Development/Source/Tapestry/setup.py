import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tapestry-dev",
    version="2.0.0dev",
    author="Zac Adam-MacEwen",
    author_email="ZAdamMac@kenshosec.com",
    description="Development branch of Tapestry for Kensho Security Labs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zadammac/tapestry",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU GPL 3",
        "Operating System :: OS Independent",
    ],
)