#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

"""
Implementation of a Histogram Diff as used by git In Python3
"""

# Implementation of the Histogram Diff as used by git in Python3
#
# Copyright (c) 2023 Kevin B. Hendricks, Stratford Ontario Canada
#
# Available undeer an MIT License.  For other license terms please
# contact the author directly for permission.
#
#  Based on studying the logic of xhistogram.c of libgit2 in addition to
#  the javascript code presented in an an absolutely wonderful explanation
#  of the basic ideas behind the Histogram Diff written by Tiark Rompf
#  in his blog article:
#        "The Histogram Diff Algorithm"
#        https://tiarkrompf.github.io/notes/?/diff-algorithm/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import gc

from .myersdiff import myers_diff


def primes(n):
    """Produces a list of prime integers smaller than or equal to n
    Args:
      n: and int representing the table size
    Returns:
      list of prime intergers smaller than or equal to n 
    """

    if n == 2:
        return [2]
    elif n < 2:
        return []
    primelist = [2]
    for maybeprime in range(3, n + 1, 2):
        is_prime = True
        for prime in primelist:
            if maybeprime % prime == 0:
                is_prime = False
        if is_prime:
            primelist.append(maybeprime)
    return primelist


class HistTableNotWellSuitedEx(Exception):
    def __init__(self, message):
        super().__init__(message)


class HistTable(object):
    """Specially designed hash table to store information needed for histogram diff

        key: a key is a tuple (typ, i) where "typ" is 'a' or 'b'
             for file_a or file_b and "i" is the line number
             this prevents long bytestring keys from having to be stored in the table
             helping to keep the memory footprint down

        value: each stored value is a tuple (ac, ai, bc, bi)
             where ac is a running count of how many times line ai occures in file_a
             and bc is a running count of how many times line bi occurs in file_b 

        Note: to prevent O(N^2) runtime "max_chain_length" is used to determine
             both when a file is unsuitable for the histogram diff approach
             and to indicate which values from file_a need not be considered as a possible
             lsb

        Raises HistTableNotWellSuitedEx(Exception) when max chain length exceeded
    """

    def __init__(self, size, lookupa, lookupb):
        self.lookupa = lookupa  # function to look up a line in file a
        self.lookupb = lookupb  # function to look up a line in file b
        primelist = primes(2*size)
        if len(primelist) > 0: 
            self.tablesize = primelist[-1]
        else:
            self.tablesize = size
        self.buckets = [None] * self.tablesize
        self.max_chain_length = 64
        
    # use python's built in hash function for speed
    # especially for long bytestrings used by diff
    def _hash(self, ky):
        return hash(ky) % self.tablesize

    def __setitem__(self, key, value):
        ky = self.parse_key(key)
        pointer = self._hash(ky)
        if not self.buckets[pointer]:
            self.buckets[pointer] = []
        else:
            if len(self.buckets[pointer]) < self.max_chain_length:
                i = 0
                for k, v in self.buckets[pointer]:
                    if self.parse_key(k) == ky:
                        self.buckets[pointer][i][1] = value
                        return True
                    i += 1
            else:
                # exceeded max chain length of allowed collisions in this bucket
                # file being diffed is not well suited for this histogram approach
                raise HistTableNotWellSuitedEx('max chin length exceeded')

        self.buckets[pointer].append([key, value])

    def __getitem__(self, key):
        ky = self.parse_key(key)
        pointer = self._hash(ky)
        if self.buckets[pointer]:
            for k, v in self.buckets[pointer]:
                if self.parse_key(k) == ky:    
                    return v
        return None

    def parse_key(self, key):
        (typ, i) = key
        if typ == 'a':
            return self.lookupa(i)
        return self.lookupb(i)
    
    def values(self, a0, a1):
        # create deterministic order to prevent random seed in
        # python hash from randomly impacting split points when ties exist
        i = a1 - 1
        while i >= a0:
            val = None
            ky = self.lookupa(i)
            pointer = self._hash(ky)
            if self.buckets[pointer]:
                for k, v in self.buckets[pointer]:
                    if self.parse_key(k) == ky:    
                        val = v
                        break;
            if val:
                if val[0] < self.max_chain_length:
                    yield val
            i-=1

        # for bucket in self.buckets: # faster but issues with random seed in python hash
        #     if bucket:
        #         for entry in bucket:
        #             # do not consider for lsb unless 'a' count less than max_chain_length
        #             if entry[1][0] < self.max_chain_length:
        #                 yield entry[1]


class HistogramDiffer(object):
    """ 
     Class to perform a Histogram Diff like those used by defaut by git
        Stores state information that allows the input files being diffed
        and the algortihm output to be effectively "globally stored" to help keep both
        memory footprint low and prevent stack overflow during recursion

        Uses a specially constructed hash table HistTable to help identify
        split points to help identify the LSB designed to detect when this
        approach is unsuitable so that a fall back to the myers diff can be used

        Each hash table entry stores both the key and its value: a tuple (ac, ai, bc, bi)
             where ac is a running count of how many times line ai occures in file_a
             and bc is a running count of how many times line bi occurs in file_b 
    """

    def __init__(self, a_lines, b_lines):
        """initialize with lineas from A and lines from B"""
        self.fds = []
        self.fas = a_lines
        self.fbs = b_lines
        self.MAX = len(self.fas) + len(self.fbs) + 1

    def lookupa(self, i):
        """lookup line i in file A"""
        return self.fas[i]

    def lookupb(self, i):
        """lookup line i in file B"""
        return self.fbs[i]

    def histdiff(self):
        """Generate histogram diff from lines of A to lines of B"""
        if self.lcs(0, len(self.fas), 0, len(self.fbs)) is False:
            # not well suited to using this histogram approach
            # handle by using myers diff
            return myers_diff(self.fas, self.fbs)
        ai = 0
        bi = 0
        res = []
        for di in range(0, len(self.fds)):
            while ai < len(self.fas) and self.fas[ai] != self.fds[di]:
                res.append(b"- " + self.fas[ai])
                ai += 1
            while bi < len(self.fbs) and self.fbs[bi] != self.fds[di]:
                res.append(b"+ " + self.fbs[bi])
                bi += 1
            res.append(b"  " + self.fds[di])
            ai += 1
            bi += 1
        while ai < len(self.fas):
            res.append(b"- " + self.fas[ai])
            ai += 1
        while bi < len(self.fbs):
            res.append(b"+ " + self.fbs[bi])
            bi += 1
        return res
    
    def common_base(self):
        """Find longest common base among file A and B"""
        if self.lcs(0, len(self.fas), 0, len(self.fbs)) is False:
            return []
        return self.fds

    def lcs(self, a0, a1, b0, b1):
        """Find longest common segment among A line range a0 to a1 and B line range b0 to b1"""
        # skip equivalent items at top and bottom
        hs = []
        ts = []
        while (a0 < a1) and (b0 < b1) and (self.fas[a0] == self.fbs[b0]):
            hs.append(self.fas[a0])
            a0 += 1 
            b0 += 1
        while (a0 < a1) and (b0 < b1) and (self.fas[a1 - 1] == self.fbs[b1 - 1]):
            ts.append(self.fas[a1 - 1])
            a1 -= 1
            b1 -= 1
        ts.reverse()
        # build histogram
        if (a1 - a0) > (b1 - b0):
            tsize = a1 - a0
        else:
            tsize = b1 - b0
        if tsize < 3:
            tsize = 3
        hist = HistTable(tsize, self.lookupa, self.lookupb)
        # first scan all of the lines of a
        # check for not well suited exceptions
        # note if it does not fire the first time here it can never fire later
        try:
            for i in range(a0, a1):
                key = ('a', i)
                if hist[key]:
                    (ac, ai, bc, bi) = hist[key]
                    hist[key] = (ac + 1, i, bc, bi)
                else:
                    hist[key] = (1, i, 0, -1)
        except HistTableNotWellSuitedEx:
            pass
            return False

        # now walk scan the lines of b looking for matches
        for i in range(b0, b1):
            key = ('b', i)
            if hist[key]:
                (ac, ai, bc, bi) = hist[key]
                hist[key] = (ac, ai, bc + 1, i)
            # if not in "a" then can never be common so no need to add this line of b
            # to hist table as it can never be an LSB split candidate
            # else:
            #    hist[key] = (0, -1, 1, i)
    
        # find lowest-occurrence item that appears in both
        cmp = self.MAX
        rec = None
        for (ac, ai, bc, bi) in hist.values(a0, a1):
            if ac > 0 and bc > 0 and ac + bc < cmp:
                rec = (ac, ai, bc, bi)
                cmp = ac + bc
        if not rec:
            self.fds = self.fds + hs + ts
            return

        (ac, ai, bc, bi) = rec

        # force garbage collect of hist now before recursion to keep
        # memory usage from regrowing too fast
        del hist
        gc.collect()
    
        self.fds = self.fds + hs
        self.lcs(a0, ai, b0, bi)
        self.fds = self.fds + [self.fas[ai]]
        self.lcs(ai + 1, a1, bi + 1, b1)
        self.fds = self.fds + ts
        return True


def main():
    """ Uses the Histogram diff algorithm to produce the diff from file a to file b
        Args:
          from_path to file a
          to_path to file b
        Returns 0:
          prints the diff of from_file to to_file
          All lines returned are preceded by a two character string
          indicating the required change:
          b'+ ' - insert, b'- ' - delete, b'  ' - keep
    """

    argv = sys.argv
    if len(argv) != 3:
        print("histogramdiff.py from_path to_path")
        print(argv)
        return
    fromfile = argv[1]
    tofile = argv[2]
    # this could be used on text with any encoding (even mixed) so treat
    # all as bytestrings
    try:
        with open(fromfile, 'rb') as ff:
            a = ff.read()
        with open(tofile, 'rb') as tf:
            b = tf.read()
    except Exception:
        a, b = b'', b''
        pass
    a_lines = a.splitlines(True)
    b_lines = b.splitlines(True)
    hdiffer = HistogramDiffer(a_lines, b_lines)
    res = hdiffer.histdiff()
    print(b''.join(res).decode('utf-8'), end="")

    # now use histogram base to generate a common base
    print("\n\ncommon base\n")
    hdiffer2 = HistogramDiffer(a_lines, b_lines)
    res = hdiffer2.common_base()
    print(b''.join(res).decode('utf-8'), end="")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

