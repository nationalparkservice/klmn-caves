#!/usr/bin/env python2
"""
Create or view plots of cave climate data.

hobo_plot.py CAVE...
    Plot all the sites for the specified caves and save as .PNG images

hobo_plot.py CAVE_site
    Plot and interactively view the data for the specified cave site

2016 David A. Riggs, LABE Physical Science Tech
"""

from time import time
tstart = time()
import sys, os, os.path

import pandas as pd
import numpy as np
import matplotlib.pyplot as pyplot
from matplotlib import gridspec
pyplot.style.use('ggplot')
print 'Loading dependencies took %.2fs\n' % (time() - tstart)


def _load_modified_csv(fname):
    """Load our own modified CSV format data into a Pandas DataFrame"""
    dataframe = pd.read_csv(fname, index_col=0, parse_dates=True)
    dataframe.sort_index(inplace=True)
    return dataframe

def _load_hoboware_csv(fname):
    """Load direct-from-HOBOWare CSV format data into a Pandas DataFrame"""
    dataframe = pd.read_csv(fname, index_col=1, parse_dates=True, skiprows=1)
    tempcol, rhcol, tscol, battcol = None, None, None, None
    for colname in dataframe.columns:
        if colname.startswith('Temp,'):
            tempcol = colname
        elif colname.startswith('RH,'):
            rhcol = colname
        elif colname.startswith('Date Time'):
            tscol = colname
        elif colname.startswith('Batt'):
            battcol = colname
    newcols = {tempcol:'Temperature', rhcol:'RH', tscol:'DateTime', battcol:'Battery'}
    dataframe.rename(columns=newcols, inplace=True)
    dataframe.sort_index(inplace=True)
    if 'Battery' not in dataframe.columns:
        dataframe['Battery'] = None
    return dataframe

def load(fname):
    """Load a .CSV file into a Pandas DataFrame"""
    if 'Plot Title:' in open(fname,'r').readline():
        return _load_hoboware_csv(fname)
    else:
        return _load_modified_csv(fname)
    

def hobo_plot(fname, interactive=False, output_format='png'):
    """Plot a file"""
    print 'Plotting %s...' % fname,
    data = load(fname)
    #daily_avg = data.resample('D', how='mean')
    daily_med = data.resample('D').median()
    daily_max = data.resample('D').max()
    daily_min = data.resample('D').min()

    fig = pyplot.figure()
    title = os.path.basename(fname).rsplit('.',1)[0].replace('_',' ')
    fig.suptitle('Lava Beds National Monument, Cave I&M - '+title, fontsize=14)
    
    gs = gridspec.GridSpec(3, 1, height_ratios=[3, 3, 1])
    ax0 = pyplot.subplot(gs[0])
    ax1 = pyplot.subplot(gs[1], sharex=ax0)
    ax2 = pyplot.subplot(gs[2], sharex=ax0)
    
    ax0.set_title(u'Temperature (\N{DEGREE SIGN}F)', fontsize=12)
    ax0.fill_between(daily_min['Temperature'].index, daily_min['Temperature'], daily_max['Temperature'], color='darkgrey')
    ax0.plot(daily_min['Temperature'], color='b')
    ax0.plot(daily_max['Temperature'], color='r')
    ax0.plot(daily_med['Temperature'], color='black')
    ymin, ymax = ax0.get_ylim()
    if ymin <= 32.0 <= ymax:
        ax0.axhline(32.0, color='b', linestyle='--', linewidth=0.5, zorder=0.75)
    ax0.xaxis.set_ticks_position('bottom')
    pyplot.setp(ax0.get_xticklabels(), fontsize=6, visible=False)

    # linear regression line
    #import matplotlib.dates as mdates
    #x = mdates.date2num(daily_med.index.to_pydatetime())  # hack!
    #fit = np.polyfit(x, daily_med['Temperature'], deg=1)
    #poly = np.poly1d(fit)
    #y = poly(x)
    #ax0.plot(daily_med.index, y)

    ax1.set_title('Relative Humidity (%)', fontsize=12)
    ax1.fill_between(daily_min['RH'].index, daily_min['RH'], daily_max['RH'], color='darkgrey')
    ax1.plot(daily_min['RH'], color='b')
    ax1.plot(daily_max['RH'], color='r')
    ax1.plot(daily_med['RH'], color='black')

    ymin, ymax = ax1.get_ylim()
    if ymax > 99.5:
        # scale Y axis if this is a 100% flatline plot
        ax1.set_ylim(ymin, 101)
        if ymin >= 90:
            ax1.set_ylim(89, 101)

    for rh, color in zip([1,25,50,75,100], [(1,0,0), (0.75,0,0.25), (0.5,0,0.5), (0.25,0,0.75), (0,0,1)]):
        if ymin <= rh <= ymax:
            ax1.axhline(rh, color=color, linestyle='--', linewidth=0.5, zorder=0.75)
    ax1.xaxis.set_ticks_position('bottom')
    pyplot.setp(ax1.get_xticklabels(), fontsize=6, visible=False)

    ax2.set_title('Battery (V)', fontsize=12)
    ax2.fill_between(daily_min['Battery'].index, daily_min['Battery'], daily_max['Battery'], color='darkgrey')
    #ax2.plot(daily_min['Battery'][daily_min['FileStart'].isnull()], color='b')
    #ax2.plot(daily_max['Battery'][daily_min['FileStart'].isnull()], color='r')
    ax2.plot(daily_min['Battery'], color='b')
    ax2.plot(daily_max['Battery'], color='r')
    #ax2.plot(daily_avg['Battery'], color='g')
    ymin, ymax = ax2.get_ylim()
    if ymin <= 2.625 <= ymax:
        ax2.axhline(2.625, color='r', linestyle='--', linewidth=0.5, zorder=0.75)
    ax2.set_ylim(2.575, 3.725)
    ax2.xaxis.set_ticks_position('bottom')

    # markers for each individual data logger
    if 'FileStart' in data.columns:
        for row in data[data['FileStart'].notnull()].itertuples():
            for ax in ax0, ax1, ax2:
                ax.axvline(row.Index, linestyle='--', linewidth=0.5, zorder=0.5, color='#808080')

    if interactive:
        pyplot.show()
    else:
        tstart = time()
        fig.set_size_inches(14, 8.5)
        outfname = fname.rsplit('.',1)[0]+'.'+output_format
        pyplot.savefig(outfname, bbox_inches='tight', dpi=150)
        telapsed = time() - tstart
        print ' %.2fs render time.' % telapsed,
    pyplot.close(fig)
    print


def cave_plot(cave):
    """Plot all files for a named cave"""
    for i, site in enumerate(('out', 'ent', 'mid', 'deep')):
        fname = '%s_%s.csv' % (cave, site)
        if os.path.exists(fname):
            hobo_plot(fname)


if __name__ == '__main__':
    from glob import glob

    if len(sys.argv) < 2:
        # plot every .CSV file we find
        for fname in glob('*.csv'):
            hobo_plot(fname)
    
    elif sys.argv[1] == '--help':
        print >> sys.stderr, 'usage:\n' \
              + '  hobo_plot.py            -  Plot all sites for all caves\n' \
              + '  hobo_plot.py CAVE_site  -  Plot just one cave-site\n' \
              + '  hobo_plot.py CAVE       -  Plot all sites for one cave\n'
        sys.exit(2)
    
    elif '_' in sys.argv[1]:
        # plot a specific cave site interactively
        fname = sys.argv[1]
        if not fname.endswith('.csv'):
            fname = fname + '.csv'
        hobo_plot(fname, interactive=True)
    
    else:
        # plot all sites for a specified cave(s)
        for cave in sys.argv[1:]:
            cave_plot(cave)
        
