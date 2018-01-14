#!/usr/bin/env python
"""
Combines all HOBO data logger CSV files into a single, sorted, and
timezone-normalized CSV file into the current directory.

hobo_combine_all.py
    Combine HOBO data logger files for all caves in the default list

hobo_combine_all.py CAVE
    Combine HOBO data logger files for the named cave.

David A. Riggs, LABE Phy Sci Tech
"""

import sys, os, os.path
import fnmatch

from hobo import HoboCSVReader


# TODO: clean these hard-coded lists up
I_AND_M_SITES = set(['BALC','BOUL','CAST','FERN','FOST','GODO','HOCH','JUHE',
                     'LAHO','LOPI','NIIN','NIRV','OVPA', 'POOF','ROCO','SEAN',
                     'SILV','SOLA','VALE','YELL'])
BAT_SITES = set(['ANGE', 'CAIC', 'INCA', 'SENT'])
ICE_SITES = set(['BIPA', 'COIC', 'CRIC', 'SKIC'])

DEFAULT_SITES = I_AND_M_SITES


def rglob(directory, pattern):
    """Recursive filename glob"""
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                yield os.path.join(root, basename)

def find_files(rootdir, sites=None):
    """Generate list of all CSV files, or optionally a specified subset"""
    for csvfname in rglob(rootdir, '*.csv'):
        #if 'Climate' not in csvfname:
        #    continue
        site = os.path.basename(csvfname).split('_',1)[0]
        if sites and site not in sites:
            continue
        yield csvfname

def split_fname(fname):
    """Split a filename into (year, cave, site, filename)"""
    basename = os.path.basename(fname)
    toks = basename.split('_')
    cave, site = toks[0].upper(), toks[1].lower()
    season = int([t for t in fname.split(os.sep) if '20' in t][0].split()[0])  # yuck!
    return season, cave, site, basename

def sort_file(fname):
    """Sort all the records in a .CSV file"""
    # WARNING: This reads and sorts the entire file in memory at once
    print 'Sorting', fname
    bakfname = fname+'.BAK'
    os.rename(fname, bakfname)
    with open(bakfname, 'rU') as infile:
        lines = infile.readlines()
    with open(fname, 'w') as outfile:
        outfile.write(lines[0])
        for line in sorted(lines[1:]):
            outfile.write(line)
    os.remove(bakfname)


HEADER = 'DateTime,Year,Month,Day,ISO_Year,ISO_Week,Temperature,RH,Battery,FileStart'
TZ = -8


def main(rootdir, outdir, sites):
    outfiles = set()

    for fname in find_files(rootdir, sites):
        if 'Climate' not in fname or 'Excel' not in fname:
            # we expect the following file structure:  `2017 Season/Climate/Excel Files/*.csv`
            continue
        
        print 'Reading', fname
        season, cave, site, basename = split_fname(fname)
        reader = HoboCSVReader(fname, as_timezone=TZ)

        outfname = os.path.join(outdir, '%s_%s.csv' % (cave, site))
        outfiles.add(outfname)
        if os.path.exists(outfname):
            print 'Writing', outfname
            outf = open(outfname, 'a')
        else:
            print 'Creating', outfname
            outf = open(outfname, 'w')
            outf.write(HEADER+'\n')

        file_start = basename
        for ts, temp, rh, batt in reader:
            iso_year, iso_week, _ = ts.isocalendar()  # ISO 8601 week definition, see: https://www.staff.science.uu.nl/~gent0113/calendar/isocalendar.htm
            outf.write(','.join((
                ts.strftime('%Y-%m-%d %H:%M:%S'),
                ts.strftime('%Y'),
                ts.strftime('%m'),
                ts.strftime('%d'),
                str(iso_year),
                str(iso_week),
                '%.3f' % temp,
                ('%.3f' % rh) if rh else '',
                ('%.2f' % batt) if batt else '',
                file_start
                )))
            outf.write('\n')
            file_start = ''

        outf.close()
        print

    for fname in sorted(outfiles):
        sort_file(fname)


if __name__ == '__main__':
    rootdir = '.'
    outdir = '.'
    sites = sys.argv[1:] if len(sys.argv) > 1 else None
    main(rootdir, outdir, sites)
