#!/usr/bin/env python
"""
Check whether our I&M HOBO data logger files have been exported as CSV.

usage:
    check_hobo_status.py 
        Check the status of all caves

    check_hobo_status.py CAVE...
        Check the status of the specified caves

2016-02-19  David A. Riggs, Physical Science Tech
"""

import sys, os, os.path


def find_dirs(rootdir):
    """Yield (year, hobodir, csvdir)"""
    for yeardir in os.listdir(rootdir):
        d = os.path.join(rootdir, yeardir)
        if not os.path.isdir(d):
            continue
        try:
            year = int(yeardir.split()[0])
        except ValueError:
            #print >> sys.stderr, 'Skipping dir %s' % yeardir
            pass
        hobodir, csvdir = None, None
        for typedir in os.listdir(d):
            if not typedir == 'Climate':
                continue
            d = os.path.join(d, typedir)
            for filedir in os.listdir(d):
                if not os.path.isdir(os.path.join(d, filedir)):
                    continue
                if filedir.lower().startswith('hobo'):
                    hobodir = os.path.join(d, filedir)
                elif filedir.lower().startswith('excel'):
                    csvdir = os.path.join(d, filedir)
            yield year, hobodir, csvdir


def get_files(d, sites=None, exts=None):
    """Get list of files in the specified directory, optionally filtering by file extension(s)"""
    l = []
    if type(exts) in (str, basestring):
        exts = [exts]
    for fname in os.listdir(d):
        file_ext = os.path.splitext(fname)[1].lower()
        if exts and file_ext not in exts:
            continue
        root = fname.split('_',1)[0]
        if sites is not None:
            if root in sites:
                l.append(fname)
        else:
            l.append(fname)
    return l


def main(rootdir, sites):
    for year, hobodir, csvdir in find_dirs(rootdir):
        hobofiles = get_files(hobodir, sites, ['.hobo', '.hproj'])
        csvfiles = get_files(csvdir, sites, '.csv')

        pct = ((len(csvfiles) / float(len(hobofiles))) * 100) if hobofiles else 0.0
        print '\n%d has %d HOBO files, %d CSV files (%.1f%%)...' % (year, len(hobofiles), len(csvfiles), pct)

        hobo_set = set(os.path.splitext(f)[0] for f in hobofiles)
        csv_set = set(os.path.splitext(f)[0].replace('_cropped','') for f in csvfiles)
        diff = hobo_set - csv_set
        if diff:
            print '\t%d missing:' % len(diff)
            for f in sorted(diff):
                print '\t\t', f
        diff2 = csv_set - hobo_set
        if diff2:
            print '\tWhoa! %d unexpected CSV files (check HOBO filename format):' % len(diff2)
            for f in sorted(diff2):
                print '\t\t', f


if __name__ == '__main__':
    rootdir = '.'
    sites = sys.argv[1:] if len(sys.argv) > 1 else None
    main(rootdir, sites)
