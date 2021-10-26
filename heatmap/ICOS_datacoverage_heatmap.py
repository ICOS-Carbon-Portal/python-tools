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


# SMALL_SIZE = 8
# MEDIUM_SIZE = 10
# BIGGER_SIZE = 12
#
# plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
# plt.rc('axes', titlesize=14)     # fontsize of the axes title
# plt.rc('axes', labelsize=12)    # fontsize of the x and y labels
# plt.rc('xtick', labelsize=10)           # fontsize of the tick labels
# plt.rc('ytick', labelsize=10)           # fontsize of the tick labels
# plt.rc('legend', fontsize=16)           # legend fontsize
# plt.rc('figure', titlesize=22)  # fontsize of the figure title


# Query the ICOS SPARQL endpoint for the raw files of the specific
# object specification(s).
def sparql_coverage(object_specs):
    query = """
            prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
            prefix prov: <http://www.w3.org/ns/prov#>
            select ?timeStart ?timeEnd ?fileName
            where {
                VALUES ?spec {"""+object_specs+"""}
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
    data = RunSparql(sparql_query=query, output_format='dict').run()
    cols = data['head']['vars']
    datatable = []
    for row in data['results']['bindings']:
        item = []
        for c in cols:
            item.append(row.get(c, {}).get('value'))
        datatable.append(item)
    df_datatable = pd.DataFrame(datatable, columns=cols)
    return df_datatable


# Procedure to make a heatmap plot for the raw data submitted by time
# and station per ICOS domain.
def plot_coverage(domain='atm'):
    # Set the parameters that differ per domain,
    # don't forget the '<' and '>' in object_specs.
    if domain == 'atm':
        object_specs = '<http://meta.icos-cp.eu/resources/cpmeta/atcLosGatosL0DataObject>' +\
                     '<http://meta.icos-cp.eu/resources/cpmeta/atcPicarroL0DataObject>'
        station_id_len = 3
        domain_title = 'Atmosphere'
    else:
        if domain == 'eco':
            object_specs = '<http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesCsv>' +\
                        ' <http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesBin>'
            station_id_len = 6
            domain_title = 'Ecosystem'
        else:
            raise RuntimeError('Unknown domain specified, only supports atm and eco')
    fig = plt.figure(figsize=(12, 6))

    # get the dataframe with the coverage times and filenames from the ICOS repo through
    # a SparQL query
    atm = sparql_coverage(object_specs)

    # some juggling to get the ISO datetimes parsed and the dataframe indexed
    # with time ready for aggregation
    atm['timeStart'] = pd.to_datetime(atm['timeStart'])
    atm['timeEnd'] = pd.to_datetime(atm['timeEnd'])
    atm['start'] = atm['timeStart']
    atm['period'] = atm['timeEnd']-atm['start']
    atm = atm.set_index('timeStart')
    atm['station'] = atm.fileName.str[0:station_id_len]
    atm = atm.drop(columns='fileName')

    # Get the list of unique station names from the list.
    stations = sorted(atm['station'].unique())
    res = pd.DataFrame()
    for station in stations:
        trn = atm.query('station=="' + station + '"')['period']
        trn = trn.rename(station)
        # Resample the dataframe in monthly bins.
        trn = trn.resample('M').sum()/dt.timedelta(days=30)*100
        # trn = trn.resample('W').sum()/dt.timedelta(days=7)*100
        # Query out measurements collected before 2017 (due to FR-Pue
        # problematic station which has data all the way to 2000).
        # trn = trn.to_frame().query('timeStart > "2017-01-01 00:00:00+00:00"')
        # Concatenate each station's data to the 'res' dataframe.
        res = pd.concat([res, trn], axis=1, sort=False)

    # Create a new index for the res dataframe using parts of the
    # previous index. This new index can be used automatically
    # by the call to heatmap() and contains dates in the form MM-YY.
    new_index = res.index.astype(str).to_list()
    for i in range(len(new_index)):
        timestamp = new_index[i]
        new_index[i] = timestamp[5:7] + '-' + timestamp[2:4]
    res.index = new_index
    res = res.transpose()

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
                         xticklabels=ceil(len(new_index)/20))
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
    plt.title('ICOS '+domain_title+' raw data coverage % per week and station')
    plt.tight_layout()
    plt.savefig('heatmap'+domain+'.pdf')
    plt.savefig('heatmap'+domain+'.png')
    plt.show()
    plt.close(fig)


# Create the plots for the two supported domains
plot_coverage('atm')
plot_coverage('eco')
