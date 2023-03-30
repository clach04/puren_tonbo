#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to process Puren Tonbo config files 

    python -m puren_tonbo.tools.ptconfig -h
    python -m puren_tonbo.tools.ptconfig --note-root /tmp
    python -m puren_tonbo.tools.ptconfig --note-root C:\tmp

TODO consider color output for config?
"""

import json
import os
from optparse import OptionParser
import sys

import puren_tonbo


is_py3 = sys.version_info >= (3,)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] [search_term] [dir_name_or_filename1] [dir_name_or_filename2...]"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("--config-file", help="Config file path")
    parser.add_option("--note-root", help="Override Directory of notes")
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")

    (options, args) = parser.parse_args(argv[1:])

    if options.list_formats:
        puren_tonbo.print_version_info()
        return 0

    config_filename = puren_tonbo.get_config_path()
    if os.path.exists(config_filename):
        config_filename_exists = True
    else:
        config_filename_exists = False
    print('config_filename %s (%s)' % (config_filename, 'exists' if config_filename_exists else 'does not exist'))

    config = puren_tonbo.get_config(options.config_file)
    if options.note_root:
            config['note_root'] = options.note_root
    print('%s' % json.dumps(config, indent=4, sort_keys=True))  # TODO color support


    return 0


if __name__ == "__main__":
    sys.exit(main())
