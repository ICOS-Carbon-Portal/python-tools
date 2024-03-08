# Standard library imports.
from datetime import timedelta, datetime
from pathlib import Path
import os
import warnings
# Related third party imports.
import matplotlib.pyplot as plt
import pandas as pd
import seaborn
# Local application/library specific imports.
from src.settings import YamlSettings
from src.constants import cpmeta, icons, general_settings
from icoscp.sparql.runsparql import RunSparql


warnings.filterwarnings('ignore')


def gimme_heatmaps(settings: YamlSettings):
    Heatmap(settings=settings)
    return


class Heatmap:

    def __init__(self, settings: YamlSettings):
        self.s = settings
        if self.s.domain == 'atc':
            self.obj_spec = cpmeta.GATOS + cpmeta.PICARRO
        elif self.s.domain == 'etc':
            self.obj_spec = cpmeta.EDDY_CSV + cpmeta.EDDY_BIN
        else:
            print(f'No heatmap implementation for {self.s.domain}'
                  f' domain. Blame Zois.')
        self.output_dir = None
        self.raw_data = None
        self.stations = sorted(self.raw_data['station'].unique())
        self.stations_info = (self.stations, self.raw_data)
        self.parsed_data = self.stations_info
        self.plot_figures()
        return

    @property
    def output_dir(self):
        return self._output_dir

    @output_dir.setter
    def output_dir(self, _):
        if self.s.version_output:
            output_dir = f'{self.s.output_dir}' \
                         f'{datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}'
        else:
            output_dir = self.s.output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self._output_dir = output_dir
        return

    @property
    def raw_data(self):
        return self._raw_data

    @raw_data.setter
    def raw_data(self, _):
        if Path(self.s.cache_path).exists():
            raw_data = pd.read_csv(self.s.cache_path)
            # todo: Find a way to read the csv file with the below
            #  changes directly using pandas arguments.
            raw_data['timeStart'] = pd.to_datetime(raw_data['timeStart'])
            raw_data['timeEnd'] = pd.to_datetime(raw_data['timeEnd'])
            raw_data['start'] = raw_data['timeStart']
            raw_data['period'] = raw_data['timeEnd'] - raw_data['start']
            raw_data = raw_data.set_index('timeStart')
        # Sparql the data only if the cache file is missing.
        else:
            print(f'Warning! Cached data ("{self.s.cache_path}") is'
                  f' missing. Querying data instead.\n This might take a '
                  f'while... ', end='')
            with open(general_settings.RAW_DATA_QUERY, mode='r') as q_handle:
                query = q_handle.read().replace('#obj_spec', self.obj_spec)
            raw_data = RunSparql(sparql_query=query,
                                 output_format='pandas').run()
            raw_data['timeStart'] = pd.to_datetime(raw_data['timeStart'])
            raw_data['timeEnd'] = pd.to_datetime(raw_data['timeEnd'])
            raw_data['start'] = raw_data['timeStart']
            raw_data['period'] = raw_data['timeEnd'] - raw_data['start']
            raw_data = raw_data.set_index('timeStart')
            # Atmosphere and Ecosystem use different formatting for
            # station names.
            raw_data['station'] = raw_data.fileName.str.split('_').str[0]
            raw_data = raw_data.drop(columns='fileName')
            print(icons.ICON_CHECK)
            raw_data.to_csv(self.s.cache_path)
        self._raw_data = raw_data
        return

    @property
    def stations_info(self):
        return self._stations_info

    @stations_info.setter
    def stations_info(self, packed_items):
        stations, data = packed_items
        stations_info = dict()
        for station in stations:
            station_full_series = \
                data.query('station == "' + station + '"')['period']
            station_full_series = station_full_series.rename(station)
            station_series = station_full_series[
                (station_full_series.index >= self.s.start) &
                (station_full_series.index <= self.s.end)
                ]
            if station_series.empty:
                generated_index = pd.date_range(start=self.s.start,
                                                end=self.s.end,
                                                freq='D', tz='UTC')
                empty_data = [
                    float("NaN") for date in range(0, len(generated_index))
                ]
                station_series = pd.Series(data=empty_data,
                                           index=generated_index)
                # if station in ['RGL', 'SNO', 'SSL']:
                #     print(f'**\n\n'
                #           f'{station} has no data for given period\n'
                #           f'This is the series:\n'
                #           f'{station_series}\n'
                #           f'**\n')
            stations_info[station] = {
                'station_series': station_series,
                'station_full_series': station_full_series
            }
        self._stations_info = stations_info
        return

    @property
    def parsed_data(self):
        return self._parsed_data

    @parsed_data.setter
    def parsed_data(self, stations_info):
        binned_data = pd.DataFrame()
        for station, station_info in stations_info.items():
            station_series = station_info['station_series']
            station_info['percentage'] = 0.0
            if station_series.isnull().all():
                binned_series = station_series.resample(self.s.group). \
                    apply(self.percentage_calculator,
                          axis=1,
                          station_info=station_info,
                          station=station
                          )
                station_info['percentage'] = 'No Data'
                station_info['y_label'] = f'  No Data'
            else:
                # Generate all missing dates (Gap days in the data).
                # Also add up each day's measurements.
                station_series = station_series.resample('D').sum()
                # Bin the station series and calculate each month's
                # percentage of data availability.
                binned_series = station_series.resample(self.s.group). \
                    apply(self.percentage_calculator,
                          axis=1,
                          station_info=station_info,
                          station=station
                          )
                station_info['percentage'] = \
                    round(station_info['percentage']/len(binned_series), 1)
                station_info['y_label'] = f'  {station_info["percentage"]} %'
            binned_data = \
                pd.concat([binned_data, binned_series], axis=1, sort=True)
        new_index = binned_data.index.to_list()
        for i in range(len(new_index)):
            timestamp = new_index[i]
            new_index[i] = \
                timestamp.strftime('%U-%y') if self.s.group == 'W' \
                else timestamp.strftime('%m-%y')
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

    def plot_figures(self):
        fig = plt.figure(figsize=(16, 10))
        # Set the frequency of the x-axis labels.
        # For some reason setting this to simply
        # len(self.parsed_data.columns) does not work and completely
        # removes the x-tick-labels. Play around with the // division
        # and the number to get the x-tick-labels to show up.
        # Todo: use this for standalone years & monthly generated output.
        x_tick_labels = 1
        # if self.s.group == 'M' and len(self.parsed_data.columns) == 12:
        #     x_tick_labels = self.parsed_data.columns.to_list()
        # else:
        #     x_tick_labels = 2

        # The bottom layer of the plot does not contain actual data
        # values. We use this layer to just plot the left y-labels and
        # the bottom x-labels.
        # empty_data = self.parsed_data.copy()
        # for column in empty_data.columns:
        #     empty_data[column].values[:] = float("Nan")
        ax = seaborn.heatmap(self.parsed_data,
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
        df_input = {'stations': [], 'percentages': []}
        for key, value in self.stations_info.items():
            formatted_percentages.append(value['y_label'])
            df_input['stations'].append(key)
            df_input['percentages'].append(value['y_label'])

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
        ax2.set_yticklabels(ax2.get_yticklabels(),
                            fontdict={'fontsize': 10, 'fontweight': 400})
        ax.set_xticklabels(ax.get_xticklabels(), rotation=80,
                           fontdict={'fontsize': 14})

        # Todo: this y-label setting must be automized. Keep in mind
        #  that for Alex's annual ICOS reporting you need to generate
        #  the standalone running year, the cumulative
        #  2020 - running-year,
        ax2.set_ylabel(
            ylabel=f'Total Percentages for {self.s.side_title_period}',
            fontdict={'fontsize': 18, 'fontweight': 'bold'},
            labelpad=10
        )
        # Todo: Y-label for cumulative report 2020-2023
        # ax2.set_ylabel(ylabel=f'Total Percentages for 2020 - 2023',
        #                fontdict={'fontsize': 18, 'fontweight': 'bold'},
        #                labelpad=10)
        # # Todo: Y-label for cumulative report 2021-2023
        # ax2.set_ylabel(ylabel=f'Total Percentages for 2021 - 2023',
        #                fontdict={'fontsize': 18, 'fontweight': 'bold'},
        #                labelpad=10)
        # # Todo: Y-label for standalone 2023
        # ax2.set_ylabel(ylabel=f'Total Percentages for 2023',
        #                fontdict={'fontsize': 18, 'fontweight': 'bold'},
        #                labelpad=10)
        # # Todo: ends here.
        plt.title(**self.get_title_args())
        plt.gcf().text(x=0, y=0, s='\n\n')
        plt.gcf().text(x=0.92, y=0.92, s=' ')
        plt.tight_layout()
        self.save_to_files(percentages=df_input)
        # Use the line below to make the plot appear in your IDE.
        # plt.show()
        plt.close(fig)
        return

    def get_title_args(self) -> dict:
        title = '\nICOS | {} raw data\ncoverage per {} and station\nfor {}'.\
            format('atmosphere' if self.s.domain == 'atc' else 'ecosystem',
                   'month' if self.s.group == 'M' else 'week',
                   self.s.title_period)
        font_dict = {'fontsize': 20,
                     'fontweight': 600,
                     'verticalalignment': 'baseline',
                     'horizontalalignment': 'center'}
        y = 1.04
        pad = '20.0'
        return {'label': title, 'fontdict': font_dict, 'y': y, 'pad': pad}

    def save_to_files(self, percentages: dict[str, list]) -> None:
        print('Generating .png and .csv files...')
        figure_path = Path(
            self.output_dir,
            f'heatmap_{self.s.domain}_'
            f'{self.s.group.lower()}_'
            f'{self.s.file_name_period}.png'
        )
        percent_path = Path(
            self.output_dir,
            f'{self.s.domain}_'
            f'{self.s.group.lower()}_'
            f'{self.s.file_name_period}_'
            f'percentages.csv'
        )
        print(f'\t{figure_path} ', end='')
        plt.savefig(figure_path)
        print(icons.ICON_CHECK)
        print(f'\t{percent_path} ', end='')
        (pd.DataFrame(percentages)).to_csv(percent_path)
        print(icons.ICON_CHECK)
        return
