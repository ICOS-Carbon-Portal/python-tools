# Format read from https://peps.python.org/pep-0008/#imports.
# Standard library imports.
from datetime import datetime

# Related third party imports.

# Local application/library specific imports.
from heatmap import Heatmap


class EcosystemHeatmap(Heatmap):
    def __init__(self, start='2017-01-01', end=datetime.now().strftime('%Y-%m-%d'), bin='M', period=None):
        self.bin = bin
        super().__init__()
        self.start = start
        self.end = end
        self.domain = 'ecosystem'
        self.object_specification = '<http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesCsv>' \
                                    + '<http://meta.icos-cp.eu/resources/cpmeta/etcEddyFluxRawSeriesBin>'
        self.query = self.object_specification
        self.raw_data_cache = 'input-files/etc_raw_data.csv'
        self.stations = self.raw_data_cache
        self.stations_info = (self.stations, self.raw_data_cache)
        self.parsed_data = (self.stations_info, self.bin)
        self.period = period
        self.plot_figures()
        return