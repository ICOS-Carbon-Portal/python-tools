import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors
import xarray
import geopandas as gpd

def plot_var(emis,var:str,vmin=1,vmax=10000,city='Zürich'):
    xarr=emis[var]
    df = xarr.to_dataframe().reset_index()
    gdf = gpd.GeoDataFrame(df[var], 
                           geometry=gpd.points_from_xy(df.lon,df.lat),
                           crs="EPSG:4326")
    fig, ax = plt.subplots(1, figsize=(9, 9))
    cmap = 'viridis'
    ax.axis('off')
    ax = gdf.to_crs('EPSG:3857').plot(ax=ax,
                                      column=var,
                                      markersize=10,
                                      norm=matplotlib.colors.LogNorm(vmin,vmax),
                                      edgecolor='0.2', 
                                      linewidth=0,
                                      alpha=0.7)
    cx.add_basemap(ax)
    sm = plt.cm.ScalarMappable(norm=matplotlib.colors.LogNorm(vmin,vmax), cmap=cmap)
    # Empty array for the data range
    sm._A = []
    # Add the colorbar to the figure
    cbaxes = fig.add_axes([1.0, 0.45, 0.02, 0.4])
    cbar = fig.colorbar(sm, cax=cbaxes, label=emis[var].comment+'\n'+emis[var].units)
    ax.set_title('ICOS Cities\n'+city+': '+emis[var].long_name)
    fig.show()
    fig.savefig(var+'.png', dpi=150, bbox_inches='tight')
    
emis=xarray.open_dataset('~/jupyter3/paul/emissions/zurich_cropped_100x100_mapLuft_2020_v1.3.nc') 
plot_var(emis,'emi_CO2_all_sectors')
plot_var(emis,'emi_CH4_all_sectors',0.0001,1)
plot_var(emis,'emi_N2O_all_sectors',0.00001,0.1)
plot_var(emis,'emi_NOx_all_sectors',0.001,10)
plot_var(emis,'emi_PM10ex_all_sectors',0.00001,0.2)
plot_var(emis,'emi_PM25ex_all_sectors',0.00001,0.2)
