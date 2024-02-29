## ICOS Heatmaps
A small application to fetch and plot raw data from the ICOS Carbon Portal as submitted by the measurement stations of 
the Ecosystem and Atmosphere domains.

## How to run
- Install the needed dependencies using `pip install -r requirements.txt`
- Run the `ICOS_datacoverage_heatmap.py` script using `python3 ICOS_datacoverage_heatmap.py` 

The script will automatically create heatmaps for atmosphere and ecosystem domains for the full sampling period
(starting in 2017) and for the last six months. 

If you want to specify your own time period and bins, then you need to instantiate the `AtmosphereHeatmap` or the 
`EcosystemHeatmap` subclass and use your custom `start`, `end`, and `bin` arguments. Here is a minimal example of how
to do exactly that:
```python
import atmosphere_heatmap


custom_start = '2020-06-25'
custom_end = '2021-05-28'
# The value of the bin argument for the heatmap can only be set to 'M' 
# or 'W' for monthly of weekly bins respectively.  
custom_bin = 'M'

# Generate atmosphere heatmaps binned monthly.
atmosphere_heatmap.AtmosphereHeatmap(start=custom_start, end=custom_end, bin=custom_bin)
```

## Cached data
For sequential runs, the application uses a built-in cache of raw atmospheric and ecosystem data which is automatically
generated after the first execution of the program and is located under `input-files` directory. In order to fetch the 
latest data, please, remove the `input-files` directory. This will force the application to re-download the data from 
ICOS Carbon Portal getting you the latest updates.