#!/usr/bin/env python
"""

"""

import sys, os, os.path
import fnmatch
import csv
from datetime import datetime

from hobo import HoboCSVReader, timestamp


SITES = set(['BALC','BOUL','CAST','FERN','FOST','GODO','HOCH','JUHE','LAHO','LOPI','NIIN','NIRV','OVPA','POOF','ROCO','SEAN','SILV','SOLA','VALE','YELL'])

MIN_VOLTAGE = 2.6
MAX_TEMP = 125
MIN_TEMP = -10
MIN_RH = 2.5
MAX_RH = 101


def mean(l):
    return sum(l) / float(len(l))

def median(l):
    l = sorted(l)
    if len(l) < 1:
        return None
    if len(l) % 2:
        return l[((len(l)+1)/2)-1]
    else:
        return float(sum(l[(len(l)/2)-1:(len(l)/2)+1]))/2.0

def _ss(l):
    """sum of square deviations"""
    c = mean(l)
    return sum((x-c)**2 for x in l)

def pstdev(l):
    """Population standard deviation."""
    n = len(l)
    if n < 2:
        raise ValueError('variance requires at least two data points')
    ss = _ss(l)
    pvar = ss/n  # population variance
    return pvar**0.5


def rglob(directory, pattern):
    """Recursive filename glob"""
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                yield os.path.join(root, basename)

def find_files(rootdir):
    """Generate list of all CSV files"""
    for csvfname in rglob(rootdir, '*.csv'):
        #if 'Climate' not in csvfname:
        #    continue
        if '_Final Analysis' in csvfname:
            continue  # skip our "Final Analysis" data
        site = os.path.basename(csvfname).split('_',1)[0]
        if site not in SITES:
            continue
        yield csvfname


def split_fname(fname):
    """Split a filename into (year, cave, site, filename)"""
    basename = os.path.basename(fname)
    toks = basename.split('_')
    cave, site = toks[0], toks[1]
    season = int([t for t in fname.split('\\') if '20' in t][0].split()[0])  # yuck!
    return season, cave, site, basename


def warn(s):
    print 'WARN:\t', s


def test_file(fname):
    print '\n\n', fname
    reader = HoboCSVReader(fname)
    times, temps, rhs, batts = reader.unzip()
    rhs = [rh for rh in rhs if rh]
    print 'Loaded %d temp and RH rows' % len(temps)

    red_flag = False    

    if not any(batts):
        print 'Battery voltage not logged.'
    elif min(batts) < MIN_VOLTAGE:
        warn('Minimum voltage: %.2f' % min(batts))
        red_flag = True

    if max(temps) > MAX_TEMP:
        warn('Maximum temperature: %.1f' % max(temps))
        red_flag = True
    if min(temps) < MIN_TEMP:
        warn('Minimum temperature: %.1f' % min(temps))
        red_flag = True

    if not any(rhs):
        print 'RH not logged.'
    elif min(rhs) < MIN_RH:
        warn('Minimum RH: %.1f' % min(rhs))
        red_flag = True

    # TODO: check if final Temp is > 1stddev above median?

    return red_flag
        

def main():
    """Test all subfiles and print output"""
    rootdir = sys.argv[1]
    for csvfname in find_files(rootdir):
        test_file(csvfname)


def csv_main(outfname=None):
    """Write a CSV summary output file"""
    rootdir = sys.argv[1]
    outfile = sys.stdout if not outfname else open(outfname,'w')
    if outfname:
        print 'Writing CSV output file %s ...' % outfname
    
    print >> outfile, 'SEASON,CAVE,SITE,FNAME,SN,' + \
        'START,END,DAYS,BATT_MIN,' + \
        'TEMP_MIN,TEMP_MED,TEMP_MEAN,TEMP_STDDEV,TEMP_MAX,TEMP_RANGE,' + \
        'RH_MIN,RH_MED,RH_MEAN,RH_STDDEV,RH_MAX,RH_RANGE,RED_FLAG'
    
    for fname in find_files(rootdir):
        print fname, '...'
        season, cave, site, basename = split_fname(fname)
        reader = HoboCSVReader(fname)
        times, temps, rhs, batts = reader.unzip()
        rhs = [rh for rh in rhs if rh is not None]
        if not rhs:
            rhs = [-1, -1]  # hack for empty series
        start, end = times[0], times[-1]
        row = (season, cave, site, basename, reader.sn,
               start, end, (end - start).days,
               min(batts) if any(batts) else '',
               min(temps), median(temps), mean(temps), pstdev(temps), max(temps), max(temps) - min(temps),
               min(rhs), median(rhs), mean(rhs), pstdev(rhs), max(rhs), max(rhs) - min(rhs),
               test_file(fname) or ''
               )
        print >> outfile, ','.join(str(v) for v in row)


if __name__ == '__main__':
    #main()
    csv_main('summary.csv')
    