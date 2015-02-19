Known Issues
------------

apt seems to require a binary-i386 directory to be present. If you don't have
any i386 packages, create an empty directory with this name alongside the
sources and other architecture directories.

Troubleshooting
---------------

When using apt-get update to synchronise with an updated repository, you may
get an error of this form:

  W: GPG error: http://repo suite Release: The following signatures were invalid: BADSIG ...

This usually indicates that some files in the repository have not been signed.
Run python-apt-repo-setup.py with the "sign" command to sign the suite that is
causing the error.
