from setuptools import setup

with open("readme.md", "r") as f:
      long_description = f.read()

setup(name='tapestry',
      version='2.0.0',
      description='Tapestry Bespoke Backup Utility',
      long_description=long_description,
      author='Zac Adam-MacEwen',
      author_email='zadammac@kenshosec.com',
      url='https://www.github.com/zadammac/Tapestry',
      packages=['tapestry'],
      long_description_format="text/markdown"
     )
