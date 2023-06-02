from setuptools import setup

with open("readme.md", "r") as f:
      long_description = f.read()

setup(name='tapestry',
      version='2.2.2',
      description='Tapestry Bespoke Backup Utility',
      long_description=long_description,
      author='Zac Adam-MacEwen',
      author_email='zadammac@arcanalabs.ca',
      url='https://www.github.com/zadammac/Tapestry',
      packages=['tapestry'],
      install_requires=['python-gnupg', 'pysftp', 'paramiko', 'keyring'],
      long_description_content_type="text/markdown"
     )
