from setuptools import setup

setup(name='tapestry',
      version='2.2.2-dev1',
      description='tapestry development build - not suitable for release',
      author='Zac Adam-MacEwen',
      author_email='zadammac@arcanalabs.ca',
      url='https://www.github.com/zadammac/Tapestry',
      packages=['tapestry'],
      install_requires=['pysftp', 'python-gnupg', 'paramiko', 'keyring'],
      )
