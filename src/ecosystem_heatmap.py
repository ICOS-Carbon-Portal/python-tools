# Format read from https://peps.python.org/pep-0008/#imports.
# Standard library imports.
from datetime import datetime

# Related third party imports.

# Local application/library specific imports.
import constants as c
from heatmap import Heatmap


class EcosystemHeatmap(Heatmap):
    def __init__(self, start=c.START, end=datetime.now().strftime('%Y-%m-%d'),
                 group='M', period=None):
        self.bin = group
        super().__init__()
        self.start = start
        self.end = end
        self.domain = 'ecosystem'
        self.object_specification = c.EDDY_CSV + c.EDDY_BIN
        self.query = self.object_specification
        # Todo: this should be in the settings.
        self.raw_data_cache = 'input-files/etc_raw_data.csv'
        self.stations = self.raw_data_cache
        self.stations_info = (self.stations, self.raw_data_cache)
        self.parsed_data = (self.stations_info, self.bin)
        self.period = period
        self.plot_figures()
        return