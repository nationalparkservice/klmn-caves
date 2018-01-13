#!/usr/bin/env python
"""

"""

import sys, os, os.path
import fnmatch
import csv
from datetime import datetime


SITES = set(['BALC','BOUL','CAST','FERN','FOST','GODO','HOCH','JUHE','LAHO','LOPI','NIIN','NIRV','OVPA','POOF','ROCO','SEAN','SILV','SOLA','VALE','YELL'])

MIN_VOLTAGE = 2.6
MAX_TEMP = 125
MIN_TEMP = -10
MIN_RH = 1


def rglob(directory, pattern):
    """Recursive filename glob"""
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                yield os.path.join(root, basename)


class ValueExtractor():
    """Extracts data from data-rows in a HOBO CSV file"""

    def __init__(self, headers):
        self.headers = headers
        
    def extract(self, line):
        """Produce (timestamp, temperature, RH, battery). Values may be `None`."""
        # TODO: timezone
        itemp = 2
        irh = 3
        ibatt = 4 if 'RH' in self.headers else 3

        row = line.split(',')
        i, ts = int(row[0]), row[1]
        temp = float(row[itemp]) if row[itemp] else None
        rh = float(row[irh]) if row[irh] else None
        batt = float(row[ibatt]) if ('Batt, V' in self.headers and row[ibatt]) else None

        return ts, temp, rh, batt
        

def copy(fname):
    """
    Copy file, truncating if the data is corrupt.

    File named `BALC_mid_12345.csv`, if truncated, will be named
    `BALC_mid_12345_cropped.csv'; the original file will be backed up
    as `BALC_mid_12345.BAK`.
    """
    outfname = fname + '.NEW.csv'
    bakfname = fname + '.BAK'
    permfname = fname.rsplit('.',1)[0] + '_cropped.csv'
    inf = open(fname, 'rt')
    outf = open(outfname, 'w')
    truncated = False
    print '\n\nProcessing %s ...' % (fname)

    title = inf.readline()
    outf.write(title)

    headers = inf.readline()
    extractor = ValueExtractor(headers)
    outf.write(headers)

    # copy until we reach bad data
    for line in inf:
        if not line:
            continue  # skip blanks
        ts, temp, rh, batt = extractor.extract(line)
        if batt and batt < MIN_VOLTAGE:
            print 'Low voltage detected, truncating.  ' + line,
            truncated = True
            break
        if rh and rh <= 1.0:
            print 'Bad RH detected, truncating.  ' + line,
            truncated = True
            break
        if temp is not None and temp > MAX_TEMP:
            print 'High temperature detected, truncating.  ' + line,
            truncated = True
            break
        if temp is not None and temp < MIN_TEMP:
            print 'Low temperature detected, truncating.  ' + line,
            truncated = True
            break
        outf.write(line)

    # back up original and rename new truncated file
    outf.close()
    inf.close()
    if not truncated:
        os.remove(outfname)
    else:
        print 'Renaming truncated %s to %s .' % (os.path.basename(fname), os.path.basename(permfname))
        os.rename(fname, bakfname)
        os.rename(outfname, permfname)


if __name__ == '__main__':
    for fname in rglob(sys.argv[1], '*.csv'):
        copy(fname)
    