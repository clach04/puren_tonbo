#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
# Implementation of using a diff3 approach to perform a 3-way merge
# In Python3
#
# Based on the wonderful blog, "The If Works", by James Coglin
# See: https://blog.jcoglan.com/2017/05/08/merging-with-diff3/
#
# Copyright (c) 2020 Kevin B. Hendricks, Stratford Ontario Canada
#
# Available under the MIT License

"""Implementation of a diff3 approach to perform a 3-way merge"""

import sys
from difflib import diff_bytes, ndiff
from .myersdiff import myers_diff
from .histogramdiff import HistogramDiffer
#from .merge import MergeOptions


class MergeOptions:
    pass


def generate_common_base_file(this_file, other_file):
    """Extracts only the common lines from this_file and other_file"""
    hd = HistogramDiffer(this_file.splitlines(True), other_file.splitlines(True))
    res = hd.common_base()
    return b''.join(res)


def diff3_file_merge(this_file, other_file, base_file, moptions):
    """Merge this_file and other_file based on their common base_file
       Uses diff_type and strategy from moptions
       Args:
           this_file  - bytestring contents of a file to merge
           other_file - bytestring contents of another file to merge
           base_file  - bytestring contents of base_file common to this_file and other_file
           moptions   - MergeOptions

       Returns:
           tuple of bytestring result of merge of this_file with other_file and
           list of any conflict ranges
    """
    diff_type = moptions.diff_type
    strategy = moptions.strategy
    if not base_file:
        base_file = generate_common_base_file(this_file, other_file)
    mrg3 = Merge3Way(this_file, other_file, base_file, moptions.diff_type, strategy)
    res = mrg3.merge()
    conflicts = mrg3.get_conflicts()
    return (res, conflicts)


class Merge3Way(object):
    """class to perform a 3 way merge of this_file and other_file based
       on their common base_file
    """
    def __init__(self, this_file, other_file, base_file, diff_type, strategy):
        """Merge3Way init
           Args:
               this_file  - bytestring to be merged with other_file
               other_file - bytestring to be merged with this_file
               base_file  - btyestring of common base_file to this_file and other_file
               diff_type  - type of diff to use "myers", "ndiff", or "histogram"
               strategy   - merge strategy (ort, ort-ours, ort-theirs, resolve, resolve-ours, resolve-theirs)
                            see https://git-scm.com/docs/merge-strategies
           Returns:
               instance of Merge3Way class
        """
        self.o_file = b'base_file'
        self.a_file = b'this_file'
        self.b_file = b'other_file'
        self.o_lines = base_file.splitlines(True)
        self.a_lines = this_file.splitlines(True)
        self.b_lines = other_file.splitlines(True)
        self.strategy = strategy
        self.conflicts = []
        if diff_type.lower() == "myers":
            self.a_matches = self._myers_matches(self.o_lines, self.a_lines)
            self.b_matches = self._myers_matches(self.o_lines, self.b_lines)
        elif diff_type.lower() == "ndiff":
            self.a_matches = self._ndiff_matches(self.o_lines, self.a_lines)
            self.b_matches = self._ndiff_matches(self.o_lines, self.b_lines)
        else:
            # otherwise use histogram diff
            self.a_matches = self._histogram_matches(self.o_lines, self.a_lines)
            self.b_matches = self._histogram_matches(self.o_lines, self.b_lines)
        self.chunks = []
        self.on, self.an, self.bn = 0, 0, 0

    def get_conflicts(self):
        """Returns list of conflicts if any from merge
            where each conflict is a tuple of ranges of line numbers
            that conflict in base_file, this_file, and then other_file respectively
            ((base_file begin, end), (this_file begin,end) (other_file begin, end))
        """
        return self.conflicts

    def _ndiff_matches(self, olines, dlines):
        """Uses difflib's ndiff to find matching lines in base_file and this_file or other_file
           Args:
              olines - list of bytestrings of base_file
              dlines - list of bytestrings of either this_file or other_file
           Returns:
              dictionary mapping matching line numbers in base_file to other
        """
        on, dn = 0, 0
        matches = {}

        # See difflib.diff_bytes documentation
        # https://docs.python.org/3/library/difflib.html
        # Use this dfunc to allow ndiff to work on mixed or unknown encoded
        # byte strings
        def do_ndiff(alines, blines, fromfile, tofile, fromfiledate,
                     tofiledate, n, lineterm):
            return ndiff(alines, blines, linejunk=None, charjunk=None)

        for line in diff_bytes(do_ndiff, olines, dlines, b'base_file', b'other',
                               b' ', b' ', n=-1, lineterm=b'\n'):
            dt = line[0:2]
            if dt == b'  ':
                on += 1
                dn += 1
                matches[on] = dn
            elif dt == b'+ ':
                dn += 1
            elif dt == b'- ':
                on += 1
        return matches

    def _myers_matches(self, olines, dlines):
        """Uses myers diff implementation to find matching lines
           in base_file and this_file or other_file
           Args:
              olines - list of bytestrings of base_file
              dlines - list of bytestrings of either this_file or other_file
           Returns:
              dictionary mapping matching line numbers in base_file to other
        """
        on, dn = 0, 0
        matches = {}
        for line in myers_diff(olines, dlines):
            dt = line[0:2]
            if dt == b'  ':
                on += 1
                dn += 1
                matches[on] = dn
            elif dt == b'+ ':
                dn += 1
            elif dt == b'- ':
                on += 1
        return matches
    
    def _histogram_matches(self, olines, dlines):
        """Uses histogram diff implementation to find matching lines
           in base_file and this_file or other_file
           Args:
              olines - list of bytestrings of base_file
              dlines - list of bytestrings of either this_file or other_file
           Returns:
              dictionary mapping matching line numbers in base_file to other
        """
        on, dn = 0, 0
        matches = {}
        hd = HistogramDiffer(olines, dlines)
        for line in hd.histdiff():
            dt = line[0:2]
            if dt == b'  ':
                on += 1
                dn += 1
                matches[on] = dn
            elif dt == b'+ ':
                dn += 1
            elif dt == b'- ':
                on += 1
        return matches

    def _generate_chunks(self):
        """Generate a list of chunks where each chunk represents
           either of matching region or non-matching region
           across this_file, base_file, and other_file
        """
        while (True):
            i = self._find_next_mismatch()
            if i is None:
                self._emit_final_chunk()
                return
            if i == 1:
                o, a, b = self._find_next_match()
                if a and b:
                    self._emit_chunk(o, a, b)
                else:
                    self._emit_final_chunk()
                    return
            elif i:
                self._emit_chunk(self.on + i, self.an + i, self.bn + i)

    def _inbounds(self, i):
        """Determine if current offset i is within any of the 3 files"""
        if (self.on + i) <= len(self.o_lines):
            return True
        if (self.an + i) <= len(self.a_lines):
            return True
        if (self.bn + i) <= len(self.b_lines):
            return True
        return False

    def _ismatch(self, matchdict, offset, i):
        """Using matchdict to determine line in base_file exists
           in this_file/other_file at offset
        """
        if (self.on + i) in matchdict:
            return matchdict[self.on + i] == offset + i
        return False

    def _find_next_mismatch(self):
        """Walk chunks to find next mismatched chunk"""
        i = 1
        while self._inbounds(i) and \
                self._ismatch(self.a_matches, self.an, i) and \
                self._ismatch(self.b_matches, self.bn, i):
            i += 1
        if self._inbounds(i):
            return i
        return None

    def _find_next_match(self):
        """Find next chunk that matches across base_file, this_file, and other_file"""
        ov = self.on + 1
        while (True):
            if ov > len(self.o_lines):
                break
            if (ov in self.a_matches and ov in self.b_matches):
                break
            ov += 1
        av = bv = None
        if ov in self.a_matches:
            av = self.a_matches[ov]
        if ov in self.b_matches:
            bv = self.b_matches[ov]
        return (ov, av, bv)

    def _write_chunk(self, o_range, a_range, b_range):
        """Output merged chunk of the given ranges"""
        oc = b''.join(self.o_lines[o_range[0]:o_range[1]])
        ac = b''.join(self.a_lines[a_range[0]:a_range[1]])
        bc = b''.join(self.b_lines[b_range[0]:b_range[1]])
        if oc == ac and oc == bc:
            self.chunks.append(oc)
        elif oc == ac:
            self.chunks.append(bc)
        elif oc == bc:
            self.chunks.append(ac)
        elif ac == bc:
            self.chunks.append(ac)
        else:
            # use strategy to determine how to handle this potential conflict
            if self.strategy in ["ort-ours", "resolve-ours"]:
                self.chunks.append(ac)
            elif self.strategy in ["ort-theirs", "resolve-theirs"]:
                self.chunks.append(bc)
            else:
                # a default strategy chunk conflict - will need to hand merge
                self.conflicts.append((o_range, a_range, b_range))
                cc = b'<<<<<<< ' + self.a_file + b'\n'
                cc += ac
                # cc += b'||||||| ' + self.o_file + b'\n'
                # cc += oc
                cc += b'======= \n'
                cc += bc
                cc += b'>>>>>>> ' + self.b_file + b'\n'
                self.chunks.append(cc)

    def _emit_chunk(self, o, a, b):
        """Emit chunk at offsets o, a, b in base_file, this_file, and other_file"""
        self._write_chunk((self.on, o - 1),
                          (self.an, a - 1),
                          (self.bn, b - 1))
        self.on, self.an, self.bn = o - 1, a - 1, b - 1

    def _emit_final_chunk(self):
        """Write out any remaining chunks"""
        self._write_chunk((self.on, len(self.o_lines) + 1),
                          (self.an, len(self.a_lines) + 1),
                          (self.bn, len(self.b_lines) + 1))

    def merge(self):
        """Perform 3 way merge"""
        self._generate_chunks()
        res = b''.join(self.chunks)
        return res


def main():
    """Perform 3-Way Merge of This and Other using a common Base
          Args:
            this_file_path  - path to this_file
            other_file_path - path to other_file file
            base_file_path  - path to base_file file
            diff_type       - "myers", "ndiff", "histogram"
          Prints output of 3 way merge with any conflicts marked
    """
    argv = sys.argv
    if len(argv) < 5:
        print("diff3merge this_file_path other_file_path base_file_path myers|ndiff|histogram")
        return 0
    afile = argv[1]
    bfile = argv[2]
    ofile = argv[3]
    dtype = argv[4]
    if ofile != "__NONE__":
        with open(ofile, 'rb') as of:
            base_file = of.read()
    else:
        base_file = None
    with open(afile, 'rb') as af:
        this_file = af.read()
    with open(bfile, 'rb') as bf:
        other_file = bf.read()
    moptions = MergeOptions()
    moptions.file_merger = diff3_file_merge
    moptions.strategy = "ort"
    moptions.diff_type= dtype
    res, conflicts = diff3_file_merge(this_file, other_file, base_file, moptions)
    print(res.decode('utf-8'), end='')
    print(conflicts)  # TODO make optional
    return 0


if __name__ == '__main__':
    sys.exit(main())
