#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Web server using CherryPy/DietCherryPy to serve files via web browser

    python -m puren_tonbo.tools.ptwebcp

    $ cat pt.json 
    {
        "_version_created_with": "0.0.3.git",
        "codec": [
            "utf8",
            "cp1252"
        ],
        "default_encryption_ext": "chi",
        "default_text_ext": "txt",
        "note_root": "puren_tonbo/tests/data/"
    }

test/demo/debug urls

http://localhost:8888/view?note=pants
http://localhost:8888/view?note=aesop.chi&password=bad

http://localhost:8888/view?note=aesop.txt
http://localhost:8888/view?note=aesop.chi&password=password
http://localhost:8888/view?note=aesop_win_encryptpad.gpg&password=password

"""

import json
import os
import sys
import time


try:
    #raise ImportError  # force use of dietcherrypy
    import cherrypy
    dietcherrypy = dietcherrypy_wsgi = None
except ImportError:
    try:
        import dietcherrypy_wsgi  # https://hg.sr.ht/~clach04/dietcherrypy
        dietcherrypy = cherrypy = dietcherrypy_wsgi
        serve_file = cherrypy.serve_file
    except ImportError:
        import dietcherrypy  # https://hg.sr.ht/~clach04/dietcherrypy
        cherrypy = dietcherrypy
        dietcherrypy_wsgi = None
        serve_file = cherrypy.serve_file


import puren_tonbo


class Root(object):
    def __init__(self, config={}):
        self.config = config
        note_encoding = config['codec']
        note_root = config.get('note_root', '.')
        self.config['note_root'] = note_root

        self.notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)

    # TODO index/default for browsing with a REST style URL
    # /note/filename.txt - GET
    # /note/filename.chi - VIEW with password payload
    # /note/filename.chi - RAW / RAWSAVE? pull-down/upload raw for end to end encryption support

    def view(self, note=None, password=None, html=False):
        # note is relative pathname
        if note is None:
            return 'Missing note filename'

        ## aggressive, no caching (http 1.1) headers
        cherrypy.response.headers['Expires'] = 'Sun, 19 Nov 1978 05:00:00 GMT'
        cherrypy.response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Content-Type'] = 'text/plain'

        try:
            data = self.notes.note_contents(note, password)
        except puren_tonbo.PurenTonboException as info:
            print('%r' % info)
            return 'file IO error'
        return data
    view.exposed = True



def main(argv=None):
    if argv is None:
        argv = sys.argv

    puren_tonbo.print_version_info()
    config = puren_tonbo.get_config()  # TODO config filename as parameter
    print('%s' % json.dumps(config, indent=4, sort_keys=True))

    print('Python %s on %s' % (sys.version, sys.platform))
    print('cherrypy %s' % (cherrypy.__version__,))

    webapp = Root(config)

    # TODO server_port in config
    server_port = os.environ.get('DIFF_PORT') or 8888
    server_port = int(server_port) or 8888
    if dietcherrypy:
        cherrypy.dietcherry_start(server_host=None, server_port=server_port, root_class=webapp)
    else:
        ## CherryPy version 3.x style
        cherrypy.quickstart(webapp)

    return 0


if __name__ == "__main__":
    sys.exit(main())

