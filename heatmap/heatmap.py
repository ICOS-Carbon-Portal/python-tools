# Format read from https://peps.python.org/pep-0008/#imports.
# Standard library imports.
import datetime
from datetime import timedelta
from math import ceil
from pathlib import Path
import os
import warnings

# Related third party imports.
import matplotlib.pyplot as plt
import numpy
import pandas
import seaborn

# Local application/library specific imports.
from icoscp.sparql.runsparql import RunSparql


warnings.filterwarnings('ignore')


class Heatmap:

    def __init__(self):
        self.archives_master_dir = 'input-files'
        Path(self.archives_master_dir).mkdir(parents=True, exist_ok=True)
        self._query = None
        self._raw_data_cache = None
        self._stations = None
        self._stations_info = None
        self._parsed_data = None
        self._domain = None
        self._period = None
        self._start = None
        self._end = None
        return

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start):
        self._start = start
        return

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        self._end = end
        return

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, period):
        coverage_period = None
        if period is None:
            coverage_period = f'{self.parsed_data.columns[0][0:2]}/20{self.parsed_data.columns[0][3:]} - ' \
                              f'{self.parsed_data.columns[-1][0:2]}/20{self.parsed_data.columns[-1][3:]}'
        self._period = coverage_period
        return


    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, object_specification):
        query = (
            f"prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>\n"
            f"prefix prov: <http://www.w3.org/ns/prov#>\n"
            f"select ?timeStart ?timeEnd ?fileName\n"
            f"where {{\n"
            f"  VALUES ?spec {{{object_specification}}}\n"
            f"  ?dobj cpmeta:hasObjectSpec ?spec .\n"
            f"  ?dobj cpmeta:hasSizeInBytes ?size .\n"
            f"  ?dobj cpmeta:hasName ?fileName .\n"
            f"  ?dobj cpmeta:wasSubmittedBy/prov:endedAtTime ?submTime .\n"
            f"  ?dobj cpmeta:hasStartTime | (cpmeta:wasAcquiredBy/prov:startedAtTime) ?timeStart .\n"
            f"  ?dobj cpmeta:hasEndTime | (cpmeta:wasAcquiredBy/prov:endedAtTime) ?timeEnd .\n"
            f"  FILTER NOT EXISTS {{[] cpmeta:isNextVersionOf ?dobj}}\n"
            f"  }}\n"
            f"order by desc(?submTime)\n"
        )
        self._query = query
        return

    @property
    def raw_data_cache(self):
        return self._raw_data_cache

    @raw_data_cache.setter
    def raw_data_cache(self, path):
        if os.path.exists(path):
            obtained_data = pandas.read_csv(path)
            # todo: Find a way to read the csv file with the below
            #  changes directly using pandas arguments.
            obtained_data['timeStart'] = pandas.to_datetime(obtained_data['timeStart'])
            obtained_data['timeEnd'] = pandas.to_datetime(obtained_data['timeEnd'])
            obtained_data['start'] = obtained_data['timeStart']
            obtained_data['period'] = obtained_data['timeEnd'] - obtained_data['start']
            obtained_data = obtained_data.set_index('timeStart')
        else:
            # Sparql the data only if the cache files in the
            # input-files directory are missing.
            obtained_data = self.run_query()
            obtained_data.to_csv(path)
        self._raw_data_cache = obtained_data
        return

    @property
    def stations(self):
        return self._stations

    @stations.setter
    def stations(self, data):
        self._stations = sorted(data['station'].unique())
        return

    @property
    def stations_info(self):
        return self._stations_info

    @stations_info.setter
    def stations_info(self, packed_items):
        stations, data = packed_items
        stations_info = dict()
        for station in stations:
            station_full_series = data.query('station == "' + station + '"')['period']
            station_full_series = station_full_series.rename(station)
            station_series = station_full_series[
                (station_full_series.index >= self.start) & (station_full_series.index <= self.end)
                ]
            if station_series.empty:
                generated_index = pandas.date_range(start=self.start, end=self.end, freq='D', tz='UTC')
                empty_data = [float("NaN") for date in range(0, len(generated_index))]
                station_series = pandas.Series(data=empty_data, index=generated_index)
                # if station in ['RGL', 'SNO', 'SSL']:
                #     print(f'**\n\n'
                #           f'{station} has no data for given period\n'
                #           f'This is the series:\n'
                #           f'{station_series}\n'
                #           f'**\n')
            stations_info[station] = {'station_series': station_series, 'station_full_series': station_full_series}
        self._stations_info = stations_info
        return

    @property
    def parsed_data(self):
        return self._parsed_data

    @parsed_data.setter
    def parsed_data(self, packed_items):
        stations_info, bin = packed_items
        binned_data = pandas.DataFrame()
        for station, station_info in stations_info.items():
            station_series = station_info['station_series']
            station_info['percentage'] = 0.0
            if station_series.isnull().all():
                binned_series = station_series.resample(bin).apply(self.percentage_calculator,
                                                                   axis=1,
                                                                   station_info=station_info,
                                                                   station=station)
                station_info['percentage'] = 'No Data'
                station_info['y_label'] = f'  No Data'
            else:
                # Generate all missing dates (Gap days in the data).
                # Also add up each day's measurements.
                station_series = station_series.resample('D').sum()
                # Bin the station series and calculate each month's
                # percentage of data availability.
                binned_series = station_series.resample(bin).apply(self.percentage_calculator,
                                                                   axis=1,
                                                                   station_info=station_info,
                                                                   station=station)
                station_info['percentage'] = round(station_info['percentage']/len(binned_series), 1)
                station_info['y_label'] = f'  {station_info["percentage"]} %'
            binned_data = pandas.concat([binned_data, binned_series], axis=1, sort=True)
        new_index = binned_data.index.to_list()
        for i in range(len(new_index)):
            timestamp = new_index[i]
            new_index[i] = timestamp.strftime('%U-%y') if bin == 'W' else timestamp.strftime('%m-%y')
        binned_data.index = new_index
        parsed_data = binned_data.transpose()
        self._parsed_data = parsed_data
        return

    @staticmethod
    def percentage_calculator(interval, **kwargs):
        station = kwargs['station']
        station_info = kwargs['station_info']
        percentage = None
        # Case of station series with data in the given time period.
        if not interval.isnull().all():
            # Find the maximum measurements per interval. We calculate
            # a number of max values and then select the minimum.
            max_days = list()
            # Get the median of the interval's measurements.
            current_max_day = interval.median().round(freq="H").days
            max_days.append(current_max_day)
            if len(interval) > 1:
                # Get the median of half of the interval's
                # measurements.
                current_max_day = interval.nsmallest(len(interval) // 2).median().round(freq="H").days
                max_days.append(current_max_day)
            if not current_max_day:
                current_max_day = round(((interval.mean().round(freq="H").seconds // 3600) / 24), 1)
                max_days.append(current_max_day)
            # Extract the minimum greater than zero max day value. Only
            # if the list is full of zeroes the max day will be zero as
            # well.
            max_day = min([x for x in max_days if x > 0]) if not all(i == 0 for i in max_days) else 0
            # The sum of the actual measurements per interval.
            summation = interval.sum()
            # The total sum per interval.
            total = timedelta(days=len(interval)) * max_day
            percentage = round(100 * (summation / total), 1) if max_day else 0
            # Fix mistakes in monthly percentages due to weird values.
            # Check station 'LMP' measurements in 10/21.
            percentage = 100 if percentage > 100 else percentage
            station_info['percentage'] += percentage
            # Use the code below to debug a single station's percentages.
            # if station == 'KRE':
            #     print(
            #         f'****\n'
            #         f'Interval with {len(interval)} days\n'
            #         f'INTERVAL\n'
            #         f'{interval}\n'
            #         f'-\n'
            #         f'summation = {summation}\n'
            #         f'total = {total}\n'
            #         f'maximum day = {max_day}\n'
            #         f'Percentage = {percentage} %\n'
            #         f'****\n\n'
            #     )
        # Case of station series without data in the given time period.
        else:
            percentage = float("NaN")
            station_info['percentage'] += percentage
        return percentage

    @property
    def domain(self):
        return self._domain

    @domain.setter
    def domain(self, domain):
        self._domain = domain
        return

    def run_query(self):
        raw_data = RunSparql(sparql_query=self.query, output_format='pandas').run()
        # Convert columns to datetime and add period & station columns.
        raw_data['timeStart'] = pandas.to_datetime(raw_data['timeStart'])
        raw_data['timeEnd'] = pandas.to_datetime(raw_data['timeEnd'])
        raw_data['start'] = raw_data['timeStart']
        raw_data['period'] = raw_data['timeEnd'] - raw_data['start']
        raw_data = raw_data.set_index('timeStart')
        # Atmosphere and Ecosystem use different formatting for station names.
        raw_data['station'] = raw_data.fileName.str.split('_').str[0]
        raw_data = raw_data.drop(columns='fileName')
        return raw_data

    def plot_figures(self):
        fig = plt.figure(figsize=(16, 10))
        # Set the frequency of the x-axis labels.
        title = None
        x_tick_labels = len(self.parsed_data.columns) // 20
        file_name = f'heatmap_{self.domain[0:3]}_{self.bin.lower()}'
        title = f'\nICOS | {self.domain} raw data\ncoverage per {"month" if self.bin == "M" else "week"} and station\n'
        # The bottom layer of the plot does not contain actual data
        # values. We use this layer to just plot the left y-labels and
        # the bottom x-labels.
        empty_data = self.parsed_data.copy()
        for column in empty_data.columns:
            empty_data[column].values[:] = float("Nan")
        ax = seaborn.heatmap(pandas.DataFrame(),
                             center=95,
                             vmin=0, vmax=100,
                             cbar=False,
                             linewidths=.07,
                             yticklabels=self.stations,
                             # Circa 20 x-labels for each figure.
                             xticklabels=x_tick_labels)
        ax.yaxis.label.set_color('silver')
        ax.set_ylabel(ylabel='Stations',
                      fontdict={'fontsize': 18, 'fontweight': 'bold'},
                      labelpad=5)
        ax.set_yticklabels(ax.get_yticklabels(), fontdict={'fontsize': 10, 'fontweight': 400})
        # Rotate the x-labels.
        ax.set_xticklabels(ax.get_xticklabels(), rotation=80, fontdict={'fontsize': 14})
        formatted_percentages = list()
        for key, value in self.stations_info.items():
            formatted_percentages.append(value['y_label'])
        ax2 = ax.twinx()
        # Call the heatmap and set the center at 95% to have everything
        # lower. We have stations that run two or more instruments so
        # we can get more than 100% coverage but that is fine, by
        # setting vmax to 100%.
        ax2 = seaborn.heatmap(self.parsed_data,
                              center=95,
                              vmin=0, vmax=100,
                              cbar_kws=dict({'pad': 0.12}),
                              cmap='coolwarm_r',
                              linewidths=.07,
                              yticklabels=formatted_percentages,
                              # Circa 20 x-labels for each figure.
                              xticklabels=x_tick_labels)
        ax2.yaxis.label.set_color('silver')
        ax2.set_yticklabels(ax2.get_yticklabels(), fontdict={'fontsize': 10, 'fontweight': 400})
        ax.set_xticklabels(ax.get_xticklabels(), rotation=80, fontdict={'fontsize': 14})
        ax2.set_ylabel(ylabel=f'Total Percentages for {self.period}',
                       fontdict={'fontsize': 18, 'fontweight': 'bold'},
                       labelpad=10)
        # Finish the plot and save it.
        plt.title(label=title,
                  fontdict={'fontsize': 20,
                            'fontweight': 600,
                            'verticalalignment': 'baseline',
                            'horizontalalignment': 'center'},
                  y=1.04,
                  pad='20.0')
        plt.gcf().text(x=0, y=0, s='\n\n')
        plt.gcf().text(x=0.92, y=0.92, s=' ')
        plt.tight_layout()
        plt.savefig(f'{file_name}.pdf')
        plt.savefig(f'{file_name}.png')
        plt.show()
        plt.close(fig)
        return

