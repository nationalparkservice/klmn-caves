#!/usr/bin/env python
"""
usage: ice_shp_filter.py [SHPFILES]

Filter out all the non- ice surface points from a Compass-produced
ESRI Shapefile of our ice monitoring survey data.

2016-03-17  David A. Riggs, Physical Science Technician, Lava Beds National Monument
"""

import sys, os, os.path
from glob import glob

try:
    import shapefile
except ImportError:
    print >> sys.stderr, 'Install the required `pyshp` package:  $> pip install pyshp'
    sys.exit(2)
    

def ice_shp_filter(fname):
    outfname = fname.rsplit('.',1)[0]+'_ice_surface.shp'

    print 'Loading', fname
    reader = shapefile.Reader(fname)
    print reader.fields
    print '%d records' % len(reader.records())

    writer = shapefile.Writer(reader.shapeType)
    writer.autoBalance = 1
    for field in reader.fields[1:]:
        writer.field(*field)
    
    for i, item in enumerate(reader.shapeRecords()):
        shape, record = item.shape, item.record
        if record[1].startswith('S_'):
            print 'Including ice surface point', record[1]
            writer.point(*shape.points[0])
            writer.record(*record)
        else:
            print 'Excluding', record[1]
    
    print 'Saving file', outfname
    writer.save(outfname)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        fnames = glob('*3Dsta.shp')
    else:
        fnames = sys.argv[1:]

    for fname in fnames:
        ice_shp_filter(fname)
