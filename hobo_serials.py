#!/usr/bin/env python
#
# List all hobo serial numbers in use under a given folder
#
# usage: hobo_serials.py [DIRNAME]
#
# 2017-08-15  David A. riggs, Physical Science Technician, Lava Beds National Monument

import sys, os, os.path
import fnmatch

from hobo import HoboCSVReader


def rglob(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                yield os.path.join(root, basename)


def find_serials(rootdir='.'):
    serials = []
    for fname in rglob(rootdir, '*.csv'):
        try:
            serials.append(HoboCSVReader(fname).sn)
        except Exception as e:
            print >> sys.stderr, 'Failed reading %s: %s' % (fname, e)
    return sorted(int(s) for s in set(serials) if s)


if __name__ == '__main__':
    if len(sys.argv) > 2 or '--help' in sys.argv:
        print >> sys.stderr, 'usage: %s [DIRNAME]' % (os.path.basename(sys.argv[1]))
        sys.exit(2)
    rootdir = '.' if len(sys.argv) == 1 else sys.argv[1]
    for serial in find_serials(rootdir):
        print serial

