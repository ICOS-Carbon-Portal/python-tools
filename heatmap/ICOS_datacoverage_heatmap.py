# (c) ICOS Carbon Portal, Lund Sweden
# Author: Alex Vermeulen, alex.vermeulen@icos-ri.eu,
# Co-developer: Zois Zogopoulos, zois.zogopoulos@nateko.lu.se
# November 2021
# licence: GNU GENERAL PUBLIC LICENSE V3
#
# Create heatmap showing data coverage of raw data available from ICOS
# Carbon Portal as submitted by the measurements stations of the
# domains Ecosystem and Atmosphere.

# Standard library imports.
import datetime as dt
from math import ceil
# Related third party imports.
from icoscp.sparql.runsparql import RunSparql
import matplotlib.pyplot as plt
import pandas as pd
import seaborn  # For data visualization.


def initialise_data():
    """
    Initialise heatmap data.

    Creates the `data` dictionary and stores necessary information
    about each domain (atmosphere or ecosystem).

    Returns:
        None
    """
    # Date calculations to query measurements collected up to six
    # months ago.
    end_datetime = pd.to_datetime('now')
    six_months_timedelta = pd.Timedelta('180 days')
    start_datetime = end_datetime - six_months_timedelta
    now = end_datetime.strftime('%Y-%m-%d')
    six_months_ago = start_datetime.strftime('%Y-%m-%d')
    # All data obtained by requests or processed by the code will be
    # stored in this dictionary among other information.
    data = dict({
        'atmosphere': {
            'data': {
                'raw_data': pd.DataFrame(),
                'parsed_data': {
                    'all': pd.DataFrame(),
                    'last_six_months': pd.DataFrame()
                },
                'binned_data': {
                    'all': pd.DataFrame(),
                    'last_six_months': pd.DataFrame()
                },
                'plot_data': {
                    'all': pd.DataFrame(),
                    'last_six_months': pd.DataFrame(),
                }
            },
            'dates': {
                'now': now,
                'six_months_ago': six_months_ago
            },
            'stations_id_length': 3,
            'stations': [],
            'object_specification':
                '<http://meta.icos-cp.eu/resources/cpmeta/atcLosGatosL0DataObject>' +
                '<http://meta.icos-cp.eu/resources/cpmeta/atcPicarroL0DataObject>'
        },
        'ecosystem': {
            'data': {
                'raw_data': pd.DataFrame(),
                'parsed_data': {
                    'all': pd.DataFrame(),
                    'last_six_months': pd.DataFrame()
                },
                'binned_data': {
                    'all': pd.DataFrame(),
                    'last_six_months': pd.DataFrame()
                },
                'plot_data': {
                    'all': pd.DataFrame(),
                    'last_six_months': pd.DataFrame(),
                }
            },
            'dates': {
                'now': now,
                'six_months_ago': six_months_ago
            },
            'stations_id_length': 6,
            'stations': [],
            'object_specification':
                '<http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesCsv>' +
                '<http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesBin>'
        }})
    return data


def create_query():
    """
    Generate a sparql query.

    Uses the `object_specification` variable to create a query and
    stores the newly generated query to the `heatmap_data` dictionary.

    Returns:
        None
    """
    object_specification = heatmap_data[key]['object_specification']
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
    heatmap_data[key]['query'] = query
    return


def run_query():
    """
    Request data using the icos Sparql module.

    Uses the query generated by `create_query()` function and the icos
    python library to request raw data in pandas format and fills in
    the `heatmap_data` dictionary.

    Returns:
        None
    """
    query = heatmap_data[key]['query']
    # Run the sparql query via the icos pylib Sparql module.
    raw_data = RunSparql(sparql_query=query, output_format='pandas').run()
    heatmap_data[key]['data']['raw_data'] = raw_data
    return


def parse_data():
    """
    Parse raw data.

    Applies necessary conversions to the requested `raw_data` and
    fills in the `heatmap_data` dictionary.

    Returns:
        None
    """
    raw_data = heatmap_data[key]['data']['raw_data']
    station_id_length = heatmap_data[key]['stations_id_length']
    start = heatmap_data[key]['dates']['six_months_ago']
    end = heatmap_data[key]['dates']['now']

    parsed_data = raw_data.copy()
    # Some juggling to get the ISO datetimes parsed and the dataframe
    # indexed with time ready for aggregation.
    parsed_data['timeStart'] = pd.to_datetime(parsed_data['timeStart'])
    parsed_data['timeEnd'] = pd.to_datetime(parsed_data['timeEnd'])
    parsed_data['start'] = parsed_data['timeStart']
    parsed_data['period'] = parsed_data['timeEnd'] - parsed_data['start']
    parsed_data = parsed_data.set_index('timeStart')
    parsed_data['station'] = parsed_data.fileName.str[0:station_id_length]
    parsed_data = parsed_data.drop(columns='fileName')
    # Find all the unique station names.
    stations = sorted(parsed_data['station'].unique())
    heatmap_data[key]['data']['parsed_data']['all'] = parsed_data
    # Query the last six months of the 'parsed_data' dataframe.
    heatmap_data[key]['data']['parsed_data']['last_six_months'] = \
        parsed_data.loc[(parsed_data['start'] >= start) & (parsed_data['start'] <= end)]
    heatmap_data[key]['stations'] = stations
    return


def create_plot_data():
    """
    Create data that will be used to plot the heatmap.

    Resamples data in a monthly or a weekly manner, re-indexes the
    dataframes that will be plotted and fills in the `heatmap_data`
    dictionary.

    Returns:
        None
    """
    parsed_data = heatmap_data[key]['data']['parsed_data']
    binned_data = heatmap_data[key]['data']['binned_data']
    stations = heatmap_data[key]['stations']
    # Iterate over dataframes in 'parsed_data' and resample them.
    for parsed_data_key, parsed_dataframe in parsed_data.items():
        for station in stations:
            series = parsed_dataframe.query('station == "' + station + '"')['period']
            series = series.rename(station)
            if parsed_data_key == 'all':
                # Resample the dataframe in monthly bins.
                series = series.resample('M').sum()/dt.timedelta(days=30)*100
            else:
                # Resample the dataframe in weekly bins.
                series = series.resample('W').sum()/dt.timedelta(days=7)*100
            # Concatenate each station's data to the dataframe.
            # Warning!!! The 'parsed_data_key' does not originally
            # belong to the 'binned_data' dictionary. Instead
            # 'parsed_data' and 'binned_data' dictionaries share the
            # same keys. This might cause trouble later on.
            binned_data[parsed_data_key] = \
                pd.concat([binned_data[parsed_data_key], series], axis=1, sort=False)
    # Re-index resampled data.
    for binned_key, binned_dataframe in binned_data.items():
        new_index = binned_dataframe.index.to_list()
        for i in range(len(new_index)):
            timestamp = new_index[i]
            if binned_key == 'all':
                # Date-time index with MM-YY format.
                new_index[i] = timestamp.strftime('%m-%y')
            else:
                # Date-time index with WW-YY format.
                new_index[i] = timestamp.strftime('%U-%y')
        binned_dataframe.index = new_index
        # Transpose binned results in order to plot them.
        # Warning!!! The 'binned_key' does not originally belong to the
        # 'plot_data' dictionary. Instead 'binned_data' and 'plot_data'
        # dictionaries share the same key. This might cause trouble
        # later on.
        heatmap_data[key]['data']['plot_data'][binned_key] = binned_dataframe.transpose()
    return


def plot_figures():
    """
    Plot final data products using seaborn's heatmap.

    Returns:
        None
    """
    plot_data = heatmap_data[key]['data']['plot_data']
    stations = heatmap_data[key]['stations']
    domain = key
    for plot_key, plot_dataframe in plot_data.items():
        fig = plt.figure(figsize=(12, 6))
        # Set the frequency of the x axis labels.
        if plot_key == 'all':
            x_tick_labels = ceil(len(plot_dataframe.columns) / 20)
            domain += '_monthly'
        else:
            x_tick_labels = 1
            domain += '_weekly'
        # Call the heatmap and set the center at 95% to have everything
        # lower. We have stations that run two or more instruments so
        # we can get more than 100% coverage but that is fine, by
        # setting vmax to 100%.
        ax = seaborn.heatmap(plot_dataframe,
                             center=95,
                             vmin=0, vmax=100,
                             cmap='coolwarm_r',
                             linewidths=.05,
                             yticklabels=stations,
                             # Circa 20 x-labels for each figure.
                             xticklabels=x_tick_labels)
        # Rotate the x-labels.
        ax.set_xticklabels(ax.get_xticklabels(), rotation=80)
        # Finish the plot and save it.
        plt.title('ICOS ' + domain + ' raw data coverage % per month and station')
        plt.savefig('heatmap' + '_' + domain + '.pdf')
        plt.savefig('heatmap' + '_' + domain + '.png')
        plt.show()
        plt.close(fig)


if __name__ == '__main__':
    heatmap_data = initialise_data()
    for key in heatmap_data.keys():
        create_query()
        run_query()
        parse_data()
        create_plot_data()
        plot_figures()
