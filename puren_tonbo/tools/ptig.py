#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line interactive tool to recursively Search Puren Tonbo files (plain text and encrypted notes).
Example encryption file formats; Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.

    python -m puren_tonbo.tools.ptig -h
"""

import os
from optparse import OptionParser
import sys
import time

try:
    import colorama
except ImportError:
    colorama = None

import puren_tonbo
from puren_tonbo import SearchCancelled

is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')


def main(argv=None):
    if argv is None:
        argv = sys.argv

    # TODO refactor ptgrep to allow reuse
    puren_tonbo.print_version_info()

    return 0


if __name__ == "__main__":
    sys.exit(main())
