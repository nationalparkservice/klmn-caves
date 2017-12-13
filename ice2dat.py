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
- davies <https://pypi.python.org/pypi/davies> for writing Compass survey project files


The produced .MAK file can be opened with Fountainware Compass <http://www.fountainware.com/compass/>,
processed, and then exported as a 3D ESRI Shapefile for subsequent processing in the GIS domain.


Credits
=======

2016-03-15  David A. Riggs, Physical Science Technician, Lava Beds National Monument

As a work of the United States Government, this project is in the public domain within the United States.
"""

from __future__ import print_function  # Python 3 compatibility

import sys, os, os.path
import csv
import datetime

import xlrd

from davies import compass
from davies.survey_math import m2ft


LABE_BASE_LOC = compass.UTMLocation(624250, 4618880, 1455, zone=10, datum=compass.UTMDatum.NAD83)


def ice2survey(rows, date=None, declination=0.0, team='', survey_id='A', origin=None, cave_name='', comment=''):
    """Convert an iterable of row dicts (csv.DictReader) to a compass.Survey"""
    if survey_id.upper().startswith('S'):
        raise IllegalArgumentException("Station identifier 'S' reserved for ice surface points")
    origin = survey_id + '0' if not origin else origin
    survey = compass.Survey(date=date, declination=declination, team=team, name=survey_id, cave_name=cave_name, comment=comment)
    survey.length_units = 'M'

    for i, row in enumerate(rows):
        if not row.get('Dist m', None):
            continue
        point, azm, dist, inc = int(row['Point'] or i+1), float(row['Azm']), m2ft(float(row['Dist m'])), float(row['Inc'])
        base_to = '%s%02d' % (survey_id, point)

        # Main survey shot
        to = base_to if row.get('Down m', None) or row.get('Back m', None) else 'S_'+base_to
        shot = compass.Shot(FROM=origin, TO=to, BEARING=azm, INC=inc, LENGTH=dist)
        survey.add_shot(shot)

        # Optional "down" shot
        if row.get('Down m', None):
            down_to = 'S_d'+base_to if not row.get('Back m') else 'd'+base_to
            down = m2ft(float(row['Down m']))
            shot = compass.Shot(FROM=to, TO=down_to, BEARING=azm, INC=-90, LENGTH=down)
            survey.add_shot(shot)

        # Optional "back" shot
        if row.get('Back m', None):
            from_ = down_to if row.get('Down m', None) else to
            back_to = 'S_b'+base_to
            back = m2ft(float(row['Back m']))
            shot = compass.Shot(FROM=from_, TO=back_to, BEARING=azm, INC=0, LENGTH=back)
            survey.add_shot(shot)

    return survey


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
            row_vals = [col.value for col in self.sheet.row(i)]
            yield dict(zip(self.headers, row_vals))


def excel_survey(sheet, **kwargs):
    reader = ExcelWorksheetReader(sheet)
    origin = sheet.name.split(' ',1)[0] + '0'
    survey = ice2survey(reader, origin=origin, comment=sheet.name, **kwargs)
    return survey


def excel_tiein(sheet, project, date=None, declination=0.0, team='', cave_name='', **kwargs):
    reader = ExcelWorksheetReader(sheet)
    survey_id = 'Tie'
    survey = compass.Survey(date=date, declination=declination, team=team, name=survey_id, cave_name=cave_name, comment=sheet.name)
    survey.length_units = 'M'
    
    for row in reader:
        from_, to = row['From'], row['To']
        azm, inc = float(row['Azm']), float(row['Inc'])
        dist, comment = m2ft(row['Dist m']), row['Comment']
        shot = compass.Shot(FROM=from_, TO=to, BEARING=azm, INC=inc, LENGTH=dist, COMMENTS=comment)
        survey.add_shot(shot)
        if row.get('Alt m', None) not in (None, ''):
            loc = compass.UTMLocation(row.get('UTM East',0), row.get('UTM North',0), row.get('Alt m',0), zone=10, datum=compass.UTMDatum.NAD83)
            print('Fixed station: %s  %s' % (row['To'], loc))
            project.add_linked_station(project.linked_files[0], row['To'], loc)

    return survey


def is_tiein(sheet):
    """Is this worksheet a "tie-in survey"?"""
    return sheet.name.replace('-','').lower() == 'tiein'


def excel2datfile(excelfname, **kwargs):
    """Convert an Excel workbook into a Compass .DAT cave survey file"""    
    book = xlrd.open_workbook(excelfname)
    basefname = os.path.basename(excelfname).rsplit('.',1)[0]
    name = basefname.replace('_', ' ')
    mak = compass.Project(name, filename=basefname+'.mak')
    dat = compass.DatFile(name, filename=basefname+'.dat')
    mak.add_linked_file(dat)
    mak.set_base_location(LABE_BASE_LOC)

    for i, sheet in enumerate(book.sheets()):
        print('Sheet: %s\tRows: %d' % (sheet.name, sheet.nrows))
        if is_tiein(sheet):
            survey = excel_tiein(sheet, mak, **kwargs)
        else:
            kwargs['survey_id'] = chr(ord('A')+i)
            survey = excel_survey(sheet, **kwargs) 
        dat.add_survey(survey)

    for survey in dat:
        for line in survey._serialize():
            print(line)
        print()

    dat.write()
    print('Wrote Compass DAT file', dat.filename)

    mak.write()
    print('Wrote Compass MAK file', mak.filename)
    if not mak.fixed_stations:
        print('WARNING: No fixed tie-in station found. Elevations not relative to fixed datum!')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert ice monitoring data into Compass survey')
    parser.add_argument('file', metavar='EXCELFILE', help='ice monitoring .XLSX file')
    parser.add_argument('-d', '--date', help='survey date (YYYY-MM-DD)')
    parser.add_argument('-t', '--team', help='survey team list')
    parser.add_argument('-m', '--declination', help='magnetic declination', type=float, default=0.0)
    parser.add_argument('-c', '--cave', help='cave name', default='')
    
    args = parser.parse_args()
    date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    
    excel2datfile(args.file, date=date, declination=args.declination, team=args.team.split(','), cave_name=args.cave)


if __name__ == '__main__':
    main()
