#!/usr/bin/env python
"""
usage: ice2dat.py [-d DATE] [-t TEAM] [-m DECLINATION] [-c CAVE] EXCELFILE

Convert ice monitoring data into Compass survey

positional arguments:
  EXCELFILE             ice monitoring .XLSX file

optional arguments:
  -h, --help            show this help message and exit
  -d DATE, --date DATE  survey date (YYYY-MM-DD)
  -t TEAM, --team TEAM  survey team list
  -m DECLINATION, --declination DECLINATION
                        magnetic declination
  -c CAVE, --cave CAVE  cave name


Input File Format
=================

Each worksheet of the Excel workbook is considered a unique "survey".

The worksheet's name helps define that survey. The first "word" of the sheet
name serves as the tie-in origin. Two sheets named "A Front Room" and "A Front
Transect" will both shoot from the tie-in point "A0".

The first row of a worksheet must contain column headers.

Typical ice survey data must have (at least) the following columns:

    Point	Azm	Dist m	Inc	Down m	Back m	Comment

A worksheet with the special sheet name "Tie-In" is used to tie an ice survey
in to fixed points within the cave, or tie multiple ice surveys together. A
tie-in survey must have the following columns:

    From	To	Dist m	Azm	Inc	Comment


Requirements
============

This script requires Python <http://python.org> for execution.

Additionally, the following third-party Python libraries are required:

- xlrd <https://pypi.python.org/pypi/xlrd> for reading Excel spreadsheets
- pyshp <https://pypi.python.org/pypi/pyshp> for writing ESRI Shapefiles


The GDAL suite of tools are required for generation of the interpolated raster grid surface.
<http://gdal.org>

The produced 3D ESRI Shapefiles and GeoTIFFs can be analyzed/visualized in the GIS domain.


Credits
=======

2017-12-XX  David A. Riggs, ex- Physical Science Technician, Lava Beds National Monument

As a work of the United States Government, this project is in the public domain within the United States.
"""

from __future__ import print_function
from __future__ import division

import sys, os, os.path
import datetime
import math
import csv
import subprocess

import xlrd

import shapefile


class ExcelWorksheetReader(object):
    """
    A `csv.DictReader` compatible wrapper over an XLRD Excel Worksheet

    The worksheet's first row must be column headers.
    """

    def __init__(self, worksheet):
        self.sheet = worksheet
        self.headers = [header.value for header in worksheet.row(0)]
    
    def __iter__(self):
        for i in range(1, self.sheet.nrows):
            yield dict(zip(self.headers, [col.value for col in self.sheet.row(i)]))


def is_tiein_survey(sheet):
    """Is this worksheet a "tie-in survey"?"""
    return sheet.name.replace('-','').lower() == 'tiein'

def is_perimeter_survey(sheet):
    """Is this worksheet a main "perimiter survey"?"""
    return not is_transect_survey(sheet) and not is_tiein_survey(sheet)

def is_transect_survey(sheet):
    """Is this worksheet a secondary "transect survey"?"""
    return 'transect' in sheet.name.lower()

def find_tiein_sheet(workbook):
    """Given an Excel workbook, find the "tie-in sheet"."""
    for sheet in workbook.sheets():
        if is_tiein_survey(sheet):
            return sheet
    raise Exception('No tie-in survey sheet found!')

def find_survey_sheets(workbook):
    """Produce the individual survey sheets from an Excel workbook"""
    return filter(lambda s: not is_tiein_survey(s), workbook.sheets())

def find_perimeter_survey_sheets(workbook):
    """Produce just the "perimeter survey" sheets from a workbook"""
    return filter(is_perimeter_survey, workbook.sheets())

def find_transect_survey_sheets(workbook):
    """Produce just the "transect survey" sheets from a workbook"""
    return filter(is_transect_survey, workbook.sheets())

def tripod_station_name(sheet):
    """Guess a worksheet's tripod survey station name"""
    return sheet.name.split()[0] + '0'


def gdal_grid(perimeter_fname, point_fname, output_grid_fname):
    """
    Generate an interpolated raster grid given sparse points and a bounding perimeter.

    This spawns a new process that calls out to the `gdal_grid` and `gdalwarp` executables.

    :param str perimeter_fname:
    :param str point_fname:
    :param str output_grid_fname:
    :return:  `True` on success
    :raises subprocess.CalledProcessError:  on failure
    """
    # TODO: calculate grid size based on desired resolution

    output_grid_tmpname = os.path.splitext(output_grid_fname)[0]+'_unclipped.tif'

    # Step 1:  Generate the interpolated raster grid
    cmd = ' '.join([
        'gdal_grid',
        '-q',
        '-zfield', 'Elev',
        '-a', 'linear',
        '-l', '"%s"' % os.path.splitext(os.path.basename(point_fname))[0],
        '"%s"' % point_fname,
        '"%s"' % output_grid_tmpname,
    ])
    print(cmd)
    subprocess.check_call(cmd, shell=True)

    # Step 2:  Clip the raster by our perimeter polyline
    cmd = ' '.join([
        'gdalwarp',
        '-q',
        '-cutline', '"%s"' % perimeter_fname,
        '-dstnodata', '-999',  # raster "no data" value
        '"%s"' % output_grid_tmpname,
        '"%s"' % output_grid_fname,
    ])
    print(cmd)
    subprocess.check_call(cmd, shell=True)


def gdal_contour(grid_fname, output_contour_fname):
    """
    Generate a contour polyline given a raster grid.

    This spawns a new process that calls out to the `gdal_contour` executable.

    :param grid_fname:
    :param output_contour_fname:
    :return:  `True` on success
    :raises subprocess.CalledProcessError:  on failure
    """
    cmd = ' '.join([
        'gdal_contour',
        '-q',
        '-a', 'Elev',
        '-i', '0.1',  # contour interval in meters
        '"%s"' % grid_fname,
        '"%s"' % output_contour_fname,
    ])
    print(cmd)
    subprocess.check_call(cmd, shell=True)


class Point(object):
    __slots__ = 'x', 'y', 'z', 'name'

    def __init__(self, x, y, z, name=None):
        self.x, self.y, self.z = x, y, z
        self.name = name

    def shot(self, dist, azm, inc, down=0.0, back=0.0, name=None):
        hd = dist * math.cos(math.radians(inc))
        x2 = hd * math.sin(math.radians(azm))
        y2 = hd * math.cos(math.radians(azm))
        z2 = dist * math.sin(math.radians(inc))
        p = Point(self.x + x2, self.y + y2, self.z + z2)
        if down:
            p = p.shot(down, 0, -90)
        if back:
            p = p.shot(back, azm, 0)
        if name:
            p.name = name
        return p

    @property
    def coords(self):
        return self.x, self.y, self.z

    @property
    def __geo_interface__(self):
        return {'type': 'Point', 'coordinates': (self.x, self.y, self.z)}

    def __eq__(self, other):
        if other is None:
            return False
        return self.x, self.y, self.z, self.name == other.x, other.y, other.z, other.name

    def __repr__(self):
        return 'Point(%s, %s, %s%s)' % \
               (self.x, self.y, self.z, ', name="%s"' % self.name if self.name else '')


def excel_tiein(sheet, declination=0.0):
    """Produce a dict of station -> coordinate from our "tie-in survey"."""
    # TODO: support magnetic declination correction

    stations = {}

    for row in ExcelWorksheetReader(sheet):
        stations[row['From']] = stations.get(row['From'], None)
        if row.get('Alt m', None) not in (None, ''):
            print('Found fixed station!  %s' % row)
            stations[row['To']] = Point(row.get('UTM East',0), row.get('UTM North',0), row.get('Alt m',0))
        else:
            stations[row['To']] = stations.get(row['To'], None)

    passes = 0
    while None in stations.values():
        for row in ExcelWorksheetReader(sheet):
            from_, to = row['From'], row['To']
            azm, inc = float(row['Azm']), float(row['Inc'])
            dist, comment = row['Dist m'], row['Comment']

            from_p, to_p = stations.get(from_, None), stations.get(to, None)
            if from_p and to_p:
                continue
            elif from_p and not to_p:
                stations[to] = from_p.shot(dist, azm, inc)
            elif to_p and not from_p:
                stations[from_] = to_p.shot(dist, (azm + 180) % 360, -1 * inc)
            else:
                print('Initially unable to georeference!  %s' % stations)
        passes += 1
        if passes > 5:
            raise Exception('Unable to georeference all stations after %d passes!  %s' % (passes, stations))

    return stations


def excel_survey(sheet, origin):
    for row in ExcelWorksheetReader(sheet):
        if not row.get('Dist m', None):
            continue  # skip blanks
        name = row.get('Point', '')
        dist, azm, inc = float(row['Dist m']), float(row['Azm']), float(row['Inc'])
        down, back = row.get('Down m', 0.0), row.get('Back m', 0.0)
        yield origin.shot(dist, azm, inc, down=down, back=back, name=name)


def process(excelfname, **kwargs):
    """
    Process an Excel workbook and export the following files:

    1. ESRI Shapefile polygon layer of ice perimeter
    2. ESRI Shapefile point layer of all ice surface points
    3. CSV file of all ice surface points
    """
    basename = os.path.splitext(excelfname)[0]
    book = xlrd.open_workbook(excelfname)

    out_perimeter = shapefile.Writer(shapefile.POLYGONZ)
    out_perimeter.autobalance = True
    out_perimeter.field('Name')

    out_points = shapefile.Writer(shapefile.POINTZ)
    out_points.autobalance = True
    out_points.field('Name')
    out_points.field('Elev', 'N', decimal=4)

    out_csv = csv.writer(open(basename+'_points.csv', 'wb'))
    out_csv.writerow(['X', 'Y', 'Z'])

    fixed_stations = excel_tiein(find_tiein_sheet(book))

    for sheet in find_survey_sheets(book):
        origin = fixed_stations[tripod_station_name(sheet)]

        if is_perimeter_survey(sheet):
            print(sheet.name, '(perimeter)')
            points = list(excel_survey(sheet, origin))
            for p in points:
                out_points.record(p.name, p.z)
                out_points.point(*p.coords)
                out_csv.writerow(p.coords)
            out_perimeter.record(sheet.name)
            out_perimeter.poly([[p.coords for p in points]])

        elif is_transect_survey(sheet):
            print(sheet.name, '(transect)')
            for p in excel_survey(sheet, origin):
                out_points.record(p.name, p.z)
                out_points.point(*p.coords)
                out_csv.writerow(p.coords)

    out_perimeter.save(basename+'_perimeter.shp')
    out_points.save(basename+'_points.shp')

    gdal_grid(basename+'_perimeter.shp', basename+'_points.shp', basename+'_grid.tif')
    gdal_contour(basename+'_grid.tif', basename+'_contour.shp')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert ice monitoring data into Compass survey')
    parser.add_argument('file', metavar='EXCELFILE', help='ice monitoring .XLSX file')
    parser.add_argument('-d', '--date', help='survey date (YYYY-MM-DD)')
    parser.add_argument('-t', '--team', help='survey team list')
    parser.add_argument('-m', '--declination', help='magnetic declination', type=float, default=0.0)
    parser.add_argument('-c', '--cave', help='cave name', default='')
    
    args = parser.parse_args()
    date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date() if args.date else None
    team = args.team.split(',') if args.team else []
    
    process(args.file, date=date, declination=args.declination, team=team, cave_name=args.cave)


if __name__ == '__main__':
    main()
