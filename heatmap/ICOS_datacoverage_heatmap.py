# Format read from https://peps.python.org/pep-0008/#imports.
# Standard library imports.
from datetime import datetime

# Related third party imports.
from dateutil.relativedelta import relativedelta

# Local application/library specific imports.
import atmosphere_heatmap
import ecosystem_heatmap


now = datetime.now()
# Get current date to string.
# end = now.date().strftime('%Y-%m-%d')
end = '2022-12-31'
# Get the date six months ago to string.
# start = (now.date() + relativedelta(months=-6)).strftime('%Y-%m-%d')
start = '2022-01-01'

# Generate atmosphere heatmaps (full and six months period.)
atmosphere_heatmap.AtmosphereHeatmap(start=start, end=end, bin='M')
# atmosphere_heatmap.AtmosphereHeatmap(start=start, end=end, bin='M')
# atmosphere_heatmap.AtmosphereHeatmap(bin='M')
# Generate ecosystem heatmaps (full and six months period.)
ecosystem_heatmap.EcosystemHeatmap(start=start, end=end, bin='M')
# ecosystem_heatmap.EcosystemHeatmap(start=start, end=end, bin='M')
# ecosystem_heatmap.EcosystemHeatmap(bin='M')

