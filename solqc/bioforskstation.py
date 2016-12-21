
# -*- coding: utf-8 -*-
__author__ = 'Sigbjorn Grini'

"""
This python file contains the class BioforskStation which is a class
to handle the time series and general info of each station.

A BioforskStation can be generated with the use of BioforskStation('Aas'),
where 'Aas' is the name of one of the Bioforsk stations. The list of available
stations at this time is found in ../config/stations.cfg.
"""

import pandas as pd
import numpy as np
import configparser
from datetime import datetime
import os


class BioforskStation(object):
    """
    A container for all applications applied to the data from the
    Bioforsk Stations.

    :param name_of_station: The name of the location of the station.
    :type name_of_station: string
    :param remove_partial_years: If you want your data to not show
    	the first and last year if they are incomplete.
    :type remove_partial_years: boolean, default True

    """

    conf = configparser.RawConfigParser()

    def __init__(self, name_of_station, remove_partial_years=True, path='..'):
        """Sets up an instance"""
        self.conf.read(os.path.join(path, 'config', 'stations.cfg'))
        self.name = name_of_station
        self.data = pd.read_csv(os.path.join(path, 'data', 'raw_data',
                                             '{}.csv'.format(
                                                 name_of_station)),
                                sep=';', parse_dates=True,
                                index_col='time_measured', dayfirst=True)
        self.longitude = self.conf.getfloat(self.name, 'lon')
        self.latitude = self.conf.getfloat(self.name, 'lat')
        self.altitude = self.conf.getfloat(self.name, 'hgt')
        self.station_id = self.conf.getfloat(self.name, 'id')

        # Makes sure to fill in NaN data where there are none
        # registered in the data file
        self.data = self.data.asfreq('H')

        self.raw = self.data.copy() # Keeps the raw files
        
        if remove_partial_years:
            self.remove_partial_year()

        # Sometimes the instrument records -6999 og 6999 instead of NaN
        self.data.loc[(self.data['qo'] == -6999) |
                      (self.data['qo'] == 6999), 'qo'] = np.nan

        # Import extraterrestrial irradiation
        self.data.loc[:, 'toa'] = pd.read_csv(os.path.join(path, 'data', 'toa',
                                                           '{}toa.csv'.format(
                                                               self.name)),
                                       header=None).values

        # Import clear sky irradiation
        clear_sky = pd.read_csv(os.path.join(path, 'data', 'clear_sky',
                                             '{}clear.txt'.format(
                                                 self.name)),
                                header=None, delim_whitespace=True,
                                parse_dates=True, index_col=0, dayfirst=True)
        clear_sky.columns = ['sza', 'qo']
        self.data.loc[:, 'sza'] = clear_sky['sza'].values
        self.data.loc[:, 'clear_sky'] = clear_sky['qo'].values

        # Initializes the flags DataFrame
        self.flags = pd.DataFrame(index=self.data.index)

    def remove_partial_year(self):
        """Returns removed start and end year if not fully complete"""
        if not self.data.index[0].is_year_start:
            self.data = self.data[self.data.index.year
                                  != self.data.index[0].year]
        if not self.data.index[-1].is_year_end:
            self.data = self.data[self.data.index.year
                                  != self.data.index[-1].year]

    def count_flags_per_year(self, pesd=False):
        """
        Returns a count of all flags registered from every test in yearly sum

        :param pesd: If true the data will be percent of errorneous data.
        :type pesd: boolean, default False
        :returns: Pandas DataFrame

        """
        if pesd:
            flagged = self.flags[self.data['toa'] > 0].groupby(self.flags[
                self.data['toa'] > 0].index.year).aggregate(np.mean) * 100

            # Offset flag is a percentage of every data
            flagged.loc[:, 'Offset'] = self.flags.loc[:, 'Offset'].groupby(
                self.flags.index.year).aggregate(np.mean) * 100
            
            
        else:
            flagged = self.flags.groupby(self.flags.index.year).aggregate(sum)
            flagged['Sum'] = flagged.sum(axis=1)

        # Change column names for easier read. Changed some of the names according
        # to thesis.
        flagged.name = self.name
        flagged.index.name = 'Year'

        return flagged
        
    def count_flags_per_month(self, pesd=False):
        """
        Returns a count of all flags registered from every test in yearly sum

        :param pesd: If true the data will be percent of errorneous data.
        :type pesd: boolean, default False
        :returns: Pandas DataFrame

        """
        
        if pesd:
            flagged = self.flags[self.data['toa'] > 0].groupby(self.flags[
                self.data['toa'] > 0].index.month).aggregate(np.mean) * 100

            # Offset flag is a percentage of every data
            flagged.loc[:, 'Offset'] = self.flags.loc[:, 'Offset'].groupby(
                self.flags.index.month).aggregate(np.mean) * 100
            
            
        else:
            flagged = self.flags.groupby(
                self.flags.index.month).aggregate(sum)
            flagged.loc[:, 'Offset'] = self.flags.loc[:, 'Offset'].groupby(
                self.flags.index.month).aggregate(sum)
            flagged['Sum'] = flagged.sum(axis=1)

        flagged.index = ['January', 'February', 'March', 'April', 'May',
                         'June', 'July', 'August', 'September', 'October',
                         'November', 'December']

        flagged.name = self.name
        flagged.index.name = 'Month'

        return flagged

    def zero_out(self):
        """
        Sets all of the global irradiance values to zero if the corresponding
        toa value is zero or the registered value is negative

        """
        self.data.loc[(self.data['toa'] == 0) |
                      (self.data['qo'] < 0), 'qo'] = 0

    def flag_info(self, pesd=True, start_date='', end_date=''):
        """
        Returns info about the flagged data

        :param pesd: If true the data will be percent of errorneous data.
        :type pesd: boolean, default True
        :param start_date: Start date on the format 'yyyy-mm-dd hh:mm',
        	recursive need from years.
        :type start_date: string, default ''
        :param end_date: End date on the format 'yyyy-mm-dd hh:mm',
        	recursive need from years.
        :type end_date: string, default ''
        :returns: Pandas DataFrame

        """
        if start_date == '':
            start_date = self.flags.index[0]
        if end_date == '':
            end_date = self.flags.index[-1]

        if pesd:
            offset = np.mean(self.flags[start_date:
                                        end_date].iloc[:, :1]) * 100
            flagged = offset.append(np.mean(
                self.flags[start_date:end_date][self.data[
                    'toa'] > 0].iloc[:, 1:]) * 100)
        else:
            flagged = np.sum(self.flags[start_date:end_date])

        flag_table = pd.DataFrame(flagged.values, flagged.index)
        flag_table.columns = ["Flagged data (%)"]
        flag_table.name = self.name
        flag_table.index.name = 'Flag type'
        return flag_table

    def nan_periods(self, start_date='', end_date=''):

        """
        Returns the periods of the timeseries that contains NaN values only

        :param start_date: Start date on the format 'yyyy-mm-dd hh:mm',
        	recursive need from years.
        :type start_date: string, default ''
        :param end_date: End date on the format 'yyyy-mm-dd hh:mm',
        	recursive need from years.
        :type end_date: string, default ''
        """
        if start_date == '':
            start_date = self.flags.index[0]
        if end_date == '':
            end_date = self.flags.index[-1]

        result = pd.DataFrame(columns=['Start Date', 'End Date'])
        df_nan = self.raw[start_date:end_date][
            self.raw['qo'][start_date:end_date].isnull()]
        start = True
        end = False
        idx = 0
        for i in range(len(df_nan)):
            if start:
                start_date = df_nan.iloc[i].name
                start = False
            if not df_nan.iloc[i].name == df_nan.iloc[-1].name:
                if not (df_nan.iloc[i + 1].name -
                        df_nan.iloc[i].name == pd.Timedelta('1h')):
                    end = True
            else:
                end = True
            if end:
                end_date = df_nan.iloc[i].name
                result.loc[idx] = [start_date, end_date]
                idx += 1
                start = True
                end = False
        return result

    def flag_offset(self):
        """
        Tests whether there are negative values less than -12 and
        if any nightly values are alrger than 6.

        """
        self.flags['Offset'] = False
        test_condition = (((self.data['qo'] > 6) & (self.data['sza'] > 93))
                          | (self.data['qo'] < -12))
        self.flags.loc[test_condition, 'Offset'] = True

    def flag_U1(self):
        """
        Tests the upper boundry of the data using
        Top of Atmosphere modelled data
        Adds a boolean flag for every data point that fails the test

        """

        self.flags['U1'] = False
        test_condition = self.data['qo'] > self.data['toa']
        self.flags.loc[test_condition, 'U1'] = True

    def flag_U2(self):
        """
        Tests the upper boundry of the data using Clear Sky modelled data
        Adds a boolean flag for every data point that fails the test

        """
        self.flags['U2'] = False
        test_condition = (((self.data['qo'] > 1.1 * self.data['clear_sky']) &
                          (self.data['sza'] < 88))
                          | ((self.data['qo'] > 2 * self.data['clear_sky']) &
                              (self.data['sza'] >= 88)))
        self.flags.loc[test_condition, 'U2'] = True

    def flag_L1(self):
        """
        Tests the lower boundry of the data using
        Top of Atmosphere modeled data and the mean of sunlight data
        Adds a boolean flag for every data point that fails the test
        
        """
        self.flags['L1'] = False
        sunlight = self.data['toa'] > 0
        key = [lambda x: x.day, lambda x:  x.month, lambda x: x.year]
        relative_qo = self.data[sunlight]['qo'] / self.data[sunlight]['toa']
        day_means = relative_qo.groupby(key).transform(lambda x: x.mean())
        flag = day_means < 0.03

        # flag and sunlight have different length, but this works since they
        # both have date index
        self.flags.loc[sunlight & flag, 'L1'] = True

    def flag_L2(self):
        """
        Tests the lower boundry of the data using
        Top of Atmosphere modelled data
        Adds a boolean flag for every data point that fails the test

        """
        self.flags['L2'] = False
        flag = ((self.data['qo'].values
                < (1e-4 * (80 - self.data['sza'].values)
                   * self.data['toa'].values))
                & (self.data['sza'] <= 80))
        self.flags.loc[flag, 'L2'] = True

    def flag_difference(self):
        """
        Tests the difference between two timesteps to ensure no extreme changes
        Adds a boolean flag for every data point that fails the test

        """
        self.flags['Difference'] = False
        
        # Calculate the ratio between measured solar irradiation and
        # extraterrestrial irradiation
        relative_qo = self.data['qo'].values / self.data['toa'].values
        
        difference_qo = np.empty(len(relative_qo))
        difference_qo[0] = 0
        for i in range(len(relative_qo) - 1):
            difference_qo[i + 1] = abs(relative_qo[i + 1] - relative_qo[i])
        flag = (difference_qo >= 0.75) & (self.data['sza'].values < 80)
        self.flags.loc[flag, 'Difference'] = True

    def flag_consistency(self):
        """
        Tests the consistency of a daily value.
        Adds a boolean flag to every day that does not pass the test.

        """
        self.flags['Consistency'] = False
        sunlight = self.data['toa'] > 0
        key = [lambda x: x.day, lambda x:  x.month, lambda x: x.year]
        relative_qo = self.data[sunlight]['qo'] / self.data[sunlight]['toa']
        day_means = relative_qo.groupby(key).transform(lambda x: x.mean())
        day_stds = relative_qo.groupby(key).transform(lambda x: x.std())
        flag = (day_stds < 1. / 16. * day_means) | (day_stds > 0.80)

        # This does work even sunlight and flag have different length,
        # since index is a time series with same frequency
        self.flags.loc[sunlight & flag, 'Consistency'] = True

    def missing_values(self):
        """
        Checks whether there are missing values
        Adds a boolean flag for every missing value

        """
        self.flags['Missing values'] = False
        missing = self.data['qo'].isnull()
        self.flags.loc[missing, 'Missing values'] = True

    def get_average_year(self, visual_control_dates = [], start_date='', end_date='', quality_control=True, leap_day=False):
        """
        Returns an average year of the time series.

        The average year procedure:

        - Group all the same hour for all years together
        - Take mean of the values that are not missing
        - If all values are missing, take mean of neighbouring values
        - The first two are same procedure as for CM-SAF PVGIS

        :param visual_control_dates: python list of of all dates that are removed by visual control,
        	write as nested list: [[start_date1, end_date1], [start_date2, end_date2]]
        :type visual_control_dates: nested list default []
        :param start_date: Start date on the format 'yyyy-mm-dd hh:mm',
        	recursive need from years.
        :type start_date: string, default ''
        :param end_date: End date on the format 'yyyy-mm-dd hh:mm',
        	recursive need from years.
        :type end_date: string, default ''
        """
        
        if start_date == '':
            start_date = self.data.index[0]
        if end_date == '':
            end_date = self.data.index[-1]
        
        
        df = self.data['qo'][start_date:end_date].copy()

        if quality_control:
            df.loc[self.flags.drop(
                ['Offset', 'Consistency'], axis=1).any(axis=1)] = np.nan

            for dates in visual_control_dates:
                df.loc[dates[0]:dates[1]] = np.nan
        # Find mean for all years
        grouped = df.groupby([df.index.month, df.index.day, df.index.hour])
        avg = pd.DataFrame(data=grouped.aggregate(lambda x: np.nanmean(x)))
        
        # Need to do this to convert from MultiIndex to DateTimeIndex
        avg['date'] = avg.index.map(lambda x: datetime(2040, x[0], x[1], x[2]))
        avg = avg.set_index('date').asfreq('H')

        # Some hours do not have any quality controlled values and are therefore
        # replaced with average between the two points.
        ffill = avg.fillna(method='ffill')
        bfill = avg.fillna(method='bfill')
        avg['ffill'] = ffill
        avg['bfill'] = bfill
        avg['avg'] = avg.mean(axis=1)

        # Remove leap day
        if not leap_day:
            avg.drop(avg['2040-02-29'].index, inplace=True)
        
        # returns only the average
        return avg['avg']

    def get_pesd(self):
        """Returns the percentage of erroneous data from automatic control"""
        return self.flags[self.data['toa'] > 0].drop(
            ['Offset', 'Consistency'], axis=1).any(axis=1).mean() * 100

    def get_visual(self):
        """
        Returns the percentage of data from automatic control flag for
        visual control

        """
        return self.flags.loc[:, ['Offset', 'Consistency']].any(axis=1).mean() * 100


if __name__ == '__main__':
    station = BioforskStation('Aas')
