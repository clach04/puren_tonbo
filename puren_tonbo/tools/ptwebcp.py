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

try:
    # Python 3.8 and later
    # py3
    from html import escape as escapecgi
except ImportError:
    # py2
    from cgi import escape as escapecgi

import json
import os
import sys
import time


try:
    if os.environ.get('FORCE_DIETCHERRYPY'):  raise ImportError()  # force usage of dietcherrypy
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


def filename_no_path(in_path):
    """basically os.path.basename(), but can potentially work on a path/URI that is not OS native
    """
    pos = in_path.rfind('/')
    return in_path[pos + 1:]


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

    # TODO file metadata; size, date
    # TODO navigation links (parent directory, root directory)
    # TODO recent (recursive)
    def list(self, s=None, recursive=True):
        """s is the subdir
        """
        ## aggressive, no caching (http 1.1) headers
        cherrypy.response.headers['Expires'] = 'Sun, 19 Nov 1978 05:00:00 GMT'
        cherrypy.response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        cherrypy.response.headers['Pragma'] = 'no-cache'

        result = []
        if s:
            result.append('%s' % escapecgi(s))
            result.append('</br>')
            result.append('</br>')

        if recursive:
            if recursive in ('n', 'f', 'no', 'false'):
                recursive = False
            elif recursive in ('y', 't', 'yes', 'true'):
                recursive = True
            else:
                recursive = False
        if recursive:
            raise NotImplementedError('recursive listings')
            dirnames = []
            note_names = self.note_store.recurse_notes(sub_dir=s)  # TODO
        else:
            #import pdb ; pdb.set_trace()
            dirnames, note_names = self.notes.directory_contents(s)
        for dirname in dirnames:
            if s:
                note_sub_dir_urls_concat = s + '/' + dirname
            else:
                note_sub_dir_urls_concat = dirname
            tmp_link = '<a href="list?recursive=n&s=%s">%s</a></br>' % (note_sub_dir_urls_concat, dirname)  # TODO unicode pathnames
            result.append(tmp_link)
        for filename in note_names:
            if s:
                filename = s + '/' + filename  # TODO could end up outside (parent of) note dir (../../)
                disp_filename = filename_no_path(filename)
            else:
                disp_filename = filename
            # TODO use a table? consider right-justifying links (or maybe move left?)
            """TODO
            <a href="view?note=%s&html=true">html</a>

            <a href="markdown?note=%s">markdown note</a>

            <a href="view?edit=true&note=%s">Edit</a>
            """
            tmp_html = """%s
            <a href="view?note=%s">Raw Text</a>

            </br>
            """ % (escapecgi(disp_filename), filename, )
            #""" % (escapecgi(disp_filename), filename, filename, filename, filename, )
            result.append(tmp_html)
        cherrypy.response.headers['Content-Type'] = 'text/html'
        text_res = '\n'.join(result)  # TODO html escape......
        return text_res
    list.exposed = True


def main(argv=None):
    if argv is None:
        argv = sys.argv

    puren_tonbo.print_version_info()
    try:
        config_filename = argv[1]
    except:
        config_filename = None
    config = puren_tonbo.get_config(config_filename=config_filename)
    print('%s' % json.dumps(config, indent=4, sort_keys=True))

    print('Python %s on %s' % (sys.version, sys.platform))
    print('cherrypy %s' % (cherrypy.__version__,))

    webapp = Root(config)

    # TODO server_port in config
    server_port = os.environ.get('LISTEN_PORT') or 8888
    server_port = int(server_port) or 8888
    print('http://localhost:%d' % server_port)
    if dietcherrypy:
        cherrypy.dietcherry_start(server_host=None, server_port=server_port, root_class=webapp)
    else:
        ## CherryPy version 3.x style
        cherrypy.quickstart(webapp)

    return 0


if __name__ == "__main__":
    sys.exit(main())

