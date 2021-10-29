# (c) ICOS Carbon Portal, Lund Sweden
# Author: Alex Vermeulen, alex.vermeulen@icos-ri.eu
# May 2020
# licence: GNU GENERAL PUBLIC LICENSE V3
#
# Create heatmap showing data coverage of raw data available from ICOS Carbon Portal
# as submitted by the measurements stations of the domains Ecosystem and Atmosphere

import pandas as pd
from math import ceil
import datetime as dt
import seaborn  # For data visualization.
import matplotlib.pyplot as plt

from icoscp.sparql.runsparql import RunSparql

# todo: potentially remove these.
from pprint import pprint


# Query the ICOS SPARQL endpoint for the raw files of the specific
# object specification(s).
def sparql_coverage(object_specs):
    query = """
            prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
            prefix prov: <http://www.w3.org/ns/prov#>
            select ?timeStart ?timeEnd ?fileName
            where {
                VALUES ?spec {""" + object_specs + """}
                ?dobj cpmeta:hasObjectSpec ?spec .
                ?dobj cpmeta:hasSizeInBytes ?size .
            ?dobj cpmeta:hasName ?fileName .
            ?dobj cpmeta:wasSubmittedBy/prov:endedAtTime ?submTime .
            ?dobj cpmeta:hasStartTime | (cpmeta:wasAcquiredBy / prov:startedAtTime) ?timeStart .
            ?dobj cpmeta:hasEndTime | (cpmeta:wasAcquiredBy / prov:endedAtTime) ?timeEnd .
                FILTER NOT EXISTS {[] cpmeta:isNextVersionOf ?dobj}
            }
            order by desc(?submTime)
    """
    # Run the sparql query via the icos pylib Sparql module.
    # todo: UNCOMMENT THIS
    data = RunSparql(sparql_query=query, output_format='dict').run()

    # # todo: REMOVE THIS
    # if 'atc' in object_specs:
    #     print('tsvis')
    #     data = pd.read_csv('atm.csv')
    # else:
    #     data = pd.read_csv('eco.csv')
    # ###################

    cols = data['head']['vars']
    datatable = []
    for row in data['results']['bindings']:
        item = []
        for c in cols:
            item.append(row.get(c, {}).get('value'))
        datatable.append(item)
    df_datatable = pd.DataFrame(datatable, columns=cols)
    return df_datatable


def create_heatmap_content(data, stations):
    for station in stations:
        trn = atm.query('station=="' + station + '"')['period']
        trn = trn.rename(station)
        # Resample the dataframe in monthly bins.
        trn = trn.resample('M').sum() / dt.timedelta(days=30) * 100
        # trn = trn.resample('W').sum()/dt.timedelta(days=7)*100
        # Concatenate each station's data to the 'res' dataframe.
        res = pd.concat([res, trn], axis=1, sort=False)

    # Create a new index for the res dataframe using parts of the
    # previous index. This new index can be used automatically
    # by the call to heatmap() and contains dates in the form MM-YY.
    new_index = res.index.astype(str).to_list()
    for i in range(len(new_index)):
        timestamp = new_index[i]
        # Date-time index with MM-YY format.
        new_index[i] = timestamp[5:7] + '-' + timestamp[2:4]
    res.index = new_index
    res = res.transpose()


# Procedure to make a heatmap plot for the raw data submitted by time
# and station per ICOS domain.
def plot_coverage(domain='atm'):
    # Set the parameters that differ per domain,
    # don't forget the '<' and '>' in object_specs.
    if domain == 'atm':
        object_specs = '<http://meta.icos-cp.eu/resources/cpmeta/atcLosGatosL0DataObject>' + \
                       '<http://meta.icos-cp.eu/resources/cpmeta/atcPicarroL0DataObject>'
        station_id_len = 3
        domain_title = 'Atmosphere'
    else:
        if domain == 'eco':
            object_specs = '<http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesCsv>' + \
                           ' <http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesBin>'
            station_id_len = 6
            domain_title = 'Ecosystem'
        else:
            raise RuntimeError('Unknown domain specified, only supports atm and eco')

    # get the dataframe with the coverage times and filenames from the ICOS repo through
    # a SparQL query
    # todo: UNCOMMENT THIS?
    # atm = sparql_coverage(object_specs)

    # todo: REMOVE THIS?
    atm = pd.read_csv(domain + '.csv')

    # some juggling to get the ISO datetimes parsed and the dataframe indexed
    # with time ready for aggregation
    atm['timeStart'] = pd.to_datetime(atm['timeStart'])
    atm['timeEnd'] = pd.to_datetime(atm['timeEnd'])
    atm['start'] = atm['timeStart']
    atm['period'] = atm['timeEnd'] - atm['start']
    atm = atm.set_index('timeStart')
    atm['station'] = atm.fileName.str[0:station_id_len]
    atm = atm.drop(columns='fileName')

    # todo: update comments here.
    end_datetime = pd.to_datetime('now')
    six_months_timedelta = pd.Timedelta('180 days')
    start_datetime = end_datetime - six_months_timedelta
    end = end_datetime.strftime('%Y-%m-%d')
    start = start_datetime.strftime('%Y-%m-%d')
    atm_last_6_months = atm.loc[(atm['start'] >= start) & (atm['start'] <= end)]

    # Get the list of unique station names from the list.
    stations = sorted(atm['station'].unique())
    # res = pd.DataFrame()
    # todo: rename this function?
    # for station in stations:
    #     trn = atm.query('station=="' + station + '"')['period']
    #     trn = trn.rename(station)
    #     # Resample the dataframe in monthly bins.
    #     trn = trn.resample('M').sum()/dt.timedelta(days=30)*100
    #     # trn = trn.resample('W').sum()/dt.timedelta(days=7)*100
    #     # Concatenate each station's data to the 'res' dataframe.
    #     res = pd.concat([res, trn], axis=1, sort=False)
    #
    # # Create a new index for the res dataframe using parts of the
    # # previous index. This new index can be used automatically
    # # by the call to heatmap() and contains dates in the form MM-YY.
    # new_index = res.index.astype(str).to_list()
    # for i in range(len(new_index)):
    #     timestamp = new_index[i]
    #     # Date-time index with MM-YY format.
    #     new_index[i] = timestamp[5:7] + '-' + timestamp[2:4]
    # res.index = new_index
    # res = res.transpose()

    fig = plt.figure(figsize=(12, 6))

    # Call the heatmap and set the center at 95% to have everything
    # lower. We have stations that run two or more instruments so we
    # can get more than 100% coverage but that is fine, by setting
    # vmax to 100%.
    ax = seaborn.heatmap(res,
                         center=95,
                         vmin=0, vmax=100,
                         cmap='coolwarm_r',
                         linewidths=.05,
                         yticklabels=stations,
                         # Circa 20 x-labels for each figure.
                         xticklabels=ceil(len(new_index) / 20))
    # Rotate the x-labels.
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)

    # the heatmap does not have the x-axis as proper datetime axis so we cheat
    # to reduce the size of the labels and have them only one per month
    # at about the right place
    # xticklabels = ax.get_xticklabels()
    # for label in xticklabels:
    #     text = label.get_text()
    #     label.set_text(text[5:8]+text[2:4])
    # ax.set_xticklabels(xticklabels)

    # now finish the plot and save it
    plt.title('ICOS ' + domain_title + ' raw data coverage % per week and station')
    # plt.tight_layout()
    # plt.savefig('heatmap'+domain+'.pdf')
    # plt.savefig('heatmap'+domain+'.png')
    plt.show()
    plt.close(fig)


# Create the plots for the two supported domains
# plot_coverage('atm')
# plot_coverage('eco')




#     # todo: UNCOMMENT THIS
#     data = RunSparql(sparql_query=query, output_format='dict').run()
#     return {'atm': atm_object_specification, 'eco': eco_object_specification}
#
#
# def request_sparql_queries(*kwargs):
#     pass


def initialise_data():
    end_datetime = pd.to_datetime('now')
    six_months_timedelta = pd.Timedelta('180 days')
    start_datetime = end_datetime - six_months_timedelta
    now = end_datetime.strftime('%Y-%m-%d')
    six_months_ago = start_datetime.strftime('%Y-%m-%d')
    data = dict({
        'atmosphere': {
            'data': {
                'raw_data': pd.DataFrame(),
                'parsed_data': pd.DataFrame(),
                'plot_data': {
                    'monthly_binned_result': pd.DataFrame(),
                    'weekly_binned_result': pd.DataFrame()
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
                'parsed_data': pd.DataFrame(),
                'plot_data': {
                    'monthly_binned_result': pd.DataFrame(),
                    'weekly_binned_result': pd.DataFrame()
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
    query = heatmap_data[key]['query']
    # todo: UNCOMMENT THIS
    # Run the sparql query via the icos pylib Sparql module.
    # raw_data = RunSparql(sparql_query=query, output_format='pandas').run()
    ###
    # todo: REMOVE THIS
    raw_data = pd.read_csv(key + '_new.csv')
    ###
    heatmap_data[key]['data']['raw_data'] = raw_data
    # todo: REMOVE THIS
    # raw_data.to_csv(key + '_new.csv')
    return


def parse_data():
    raw_data = heatmap_data[key]['data']['raw_data']
    station_id_length = heatmap_data[key]['stations_id_length']
    start = heatmap_data[key]['dates']['six_months_ago']
    end = heatmap_data[key]['dates']['now']

    parsed_data = raw_data.copy()
    parsed_data['timeStart'] = pd.to_datetime(parsed_data['timeStart'])
    parsed_data['timeEnd'] = pd.to_datetime(parsed_data['timeEnd'])
    parsed_data['start'] = parsed_data['timeStart']
    parsed_data['period'] = parsed_data['timeEnd'] - parsed_data['start']
    parsed_data = parsed_data.set_index('timeStart')
    parsed_data['station'] = parsed_data.fileName.str[0:station_id_length]
    parsed_data = parsed_data.drop(columns='fileName')
    stations = sorted(parsed_data['station'].unique())

    heatmap_data[key]['data']['parsed_data'] = parsed_data
    heatmap_data[key]['data']['parsed_data_last_6_months'] = \
        parsed_data.loc[(parsed_data['start'] >= start) & (parsed_data['start'] <= end)]
    heatmap_data[key]['stations'] = stations
    return


def create_heatmap_data():
    stations = heatmap_data[key]['stations']
    parsed_data = heatmap_data[key]['data']['parsed_data']
    parsed_data_last_6_months = heatmap_data[key]['data']['parsed_data_last_6_months']
    monthly_binned_result = pd.DataFrame()
    weekly_binned_result = pd.DataFrame()
    for station in stations:
        series = parsed_data.query('station == "' + station + '"')['period']
        series = series.rename(station)
        # Resample the dataframe in monthly bins.
        series = series.resample('M').sum()/dt.timedelta(days=30)*100
        # Concatenate each station's data to the 'result' dataframe.
        monthly_binned_result = pd.concat([monthly_binned_result, series], axis=1, sort=False)

        series = parsed_data_last_6_months.query('station == "' + station + '"')['period']
        series = series.rename(station)
        # Resample the dataframe in weekly bins.
        series = series.resample('W').sum()/dt.timedelta(days=7)*100
        # Concatenate each station's data to the 'result' dataframe.
        weekly_binned_result = pd.concat([weekly_binned_result, series], axis=1, sort=False)

    rework_index(result_dict={'monthly': monthly_binned_result, 'weekly': weekly_binned_result})
    # Create a new index for the res dataframe using parts of the
    # previous index. This new index can be used automatically
    # by the call to heatmap() and contains dates in the form MM-YY.
    # new_index = monthly_binned_result.index.to_list()
    # for i in range(len(new_index)):
    #     timestamp = new_index[i]
    #     # Date-time index with MM-YY format.
    #     new_index[i] = timestamp.strftime('%m-%y')
    # monthly_binned_result.index = new_index
    # monthly_binned_result = monthly_binned_result.transpose()

    # new_index = weekly_binned_result.index.to_list()
    # for i in range(len(new_index)):
    #     timestamp = new_index[i]
    #     # Date-time index with WW-YY format.
    #     new_index[i] = timestamp.strftime('%U-%y')
    # weekly_binned_result.index = new_index
    # weekly_binned_result = weekly_binned_result.transpose()

    heatmap_data[key]['data']['plot_data']['monthly_binned_result'] = \
        monthly_binned_result.transpose()
    heatmap_data[key]['data']['plot_data']['weekly_binned_result'] = \
        weekly_binned_result.transpose()


def rework_index(result_dict):
    for bin_key, dataframe in zip(result_dict.keys(), result_dict.values()):
        new_index = dataframe.index.to_list()
        for i in range(len(new_index)):
            timestamp = new_index[i]
            if bin_key == 'monthly':
                # Date-time index with MM-YY format.
                new_index[i] = timestamp.strftime('%m-%y')
            else:
                # Date-time index with WW-YY format.
                new_index[i] = timestamp.strftime('%U-%y')
        dataframe.index = new_index
    return


def plot_figures():
    data_to_plot = heatmap_data[key]['data']['plot_data']['monthly_binned_result']
    data_to_plot2 = heatmap_data[key]['data']['plot_data']['weekly_binned_result']
    stations = heatmap_data[key]['stations']
    stations2 = heatmap_data[key]['stations']  # todo: THIS NEEDS FIXING stations2 != stations
    domain_title = key

    fig = plt.figure(figsize=(12, 6))

    # Call the heatmap and set the center at 95% to have everything
    # lower. We have stations that run two or more instruments so we
    # can get more than 100% coverage but that is fine, by setting
    # vmax to 100%.
    ax = seaborn.heatmap(data_to_plot,
                         center=95,
                         vmin=0, vmax=100,
                         cmap='coolwarm_r',
                         linewidths=.05,
                         yticklabels=stations,
                         # Circa 20 x-labels for each figure.
                         xticklabels=ceil(len(data_to_plot.columns) / 20))
    # Rotate the x-labels.
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)

    # now finish the plot and save it
    # plt.title('ICOS ' + domain_title + ' raw data coverage % per week and station')
    # plt.tight_layout()
    # plt.savefig('heatmap'+domain+'.pdf')
    # plt.savefig('heatmap'+domain+'.png')
    plt.show()
    plt.close(fig)

    fig = plt.figure(figsize=(12, 6))
    ax = seaborn.heatmap(data_to_plot2,
                         center=95,
                         vmin=0, vmax=100,
                         cmap='coolwarm_r',
                         linewidths=.05,
                         yticklabels=stations2,
                         # Circa 20 x-labels for each figure.
                         xticklabels=ceil(len(data_to_plot2.columns) / 20))
    # Rotate the x-labels.
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)
    plt.show()
    plt.close(fig)


heatmap_data = initialise_data()
for key in heatmap_data.keys():
    create_query()
    run_query()  # todo: FIX INSIDE FUNCTION.
    parse_data()
    create_heatmap_data()
    plot_figures()

# pprint(heatmap_data)
# print(heatmap_data['atmosphere']['data']['parsed_data_last_6_months'])
# atm_last_6_months = atm.loc[(atm['start'] >= start) & (atm['start'] <= end)]
# start = heatmap_data[key]['dates']['six_months_ago']
# print(type(start))
# parsed_data = heatmap_data['atmosphere']['data']['parsed_data']
# print(parsed_data.loc[parsed_data['start'] >= start])