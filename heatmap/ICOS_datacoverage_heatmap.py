# (c) ICOS Carbon Portal, Lund Sweden
# Author: Alex Vermeulen, alex.vermeulen@icos-ri.eu
# May 2020
# licence: GNU GENERAL PUBLIC LICENSE V3
#
# Create heatmap showing data coverage of raw data available from ICOS Carbon Portal
# as submitted by the measurements stations of the domains Ecosystem and Atmosphere

import pandas as pd
import datetime as dt
import seaborn  # for data visualization
import matplotlib.pyplot as plt
import requests

from icoscp.sparql.runsparql import RunSparql


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

    # get the list of unique station names from the list and select the data per
    # station and then aggregate and concat the data to the res dataframe that
    # we transpose to get the correct plot in seaborne heatmap
    stations = sorted(atm['station'].unique())
    res = pd.DataFrame()
    for station in stations:
        trn = atm.query('station=="' + station + '"')['period']
        trn.rename(station)
        trn = trn.resample('W').sum()/dt.timedelta(days=7)*100
        res = pd.concat([res, trn], axis=1, sort=False)
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
                         yticklabels=stations)

    # the heatmap does not have the x-axis as proper datetime axis so we cheat
    # to reduce the size of the labels and have them only one per month
    # at about the right place
    xticklabels = ax.get_xticklabels()
    for label in xticklabels:
        text = label.get_text()
        label.set_text(text[5:8]+text[2:4])
    ax.set_xticklabels(xticklabels)

    # now finish the plot and save it
    plt.title('ICOS '+domain_title+' raw data coverage % per week and station'  )
    plt.savefig('heatmap'+domain+'.pdf')
    plt.savefig('heatmap'+domain+'.png')
    plt.show()
    plt.close(fig)


# Create the plots for the two supported domains
plot_coverage('atm')
plot_coverage('eco')
