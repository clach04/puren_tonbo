#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Test suite for Puren Tonbo

Sample usage:

    ./test_chi.py -v
    ./test_chi.py -v FIXME_class_name_here

"""

import os
import sys
try:
    if sys.version_info < (2, 3):
        raise ImportError
    import unittest2
    unittest = unittest2
except ImportError:
    import unittest
    unittest2 = None

import puren_tonbo


is_py3 = sys.version_info >= (3,)


class TestIOUtil(unittest.TestCase):
    def skip(self, reason):
        """Skip current test because of `reason`.

        NOTE currently expects unittest2, and defaults to "pass" if not available.

        unittest2 does NOT work under Python 2.2.
        Could potentially use nose or py.test which has (previously) supported Python 2.2
          * nose http://python-nose.googlecode.com/svn/wiki/NoseWithPython2_2.wiki
          * py.test http://codespeak.net/pipermail/py-dev/2005-February/000203.html
        """
        #self.assertEqual(1, 0)
        if unittest2:
            raise unittest2.SkipTest(reason)
        else:
            print(reason)
            self.fail('SKIP THIS TEST: ' + reason)
            #self.assertTrue(False, reason)
            #raise Exception(reason)


def main():
    print(sys.version)
    print('')
    print('Formats:')
    print('')
    for file_extension in puren_tonbo.file_type_handlers:
        handler_class = puren_tonbo.file_type_handlers[file_extension]
        print('%17s - %s - %s' % (file_extension[1:], handler_class.__name__, handler_class.description))  # TODO description
    unittest.main()

if __name__ == '__main__':
    main()
