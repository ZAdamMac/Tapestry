"""Tapestry is a specialized backup tool for creating full-file backup packages
and storing them under conditions where the secrecy of the storage media is not
necessarily trusted. For complete usage information refer to the readme.md in
this package, or at the development repo:

github: https://www.github.com/ZAdamMac/Tapestry

"""

from . import functions as tapestry

if __name__ == "__main__":
    tapestry.runtime()
