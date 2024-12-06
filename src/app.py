# Standard library imports.
from io import BytesIO
import base64
import os

# Related third party imports.
from flask import Flask, render_template, request

# Local application/library specific imports.
from settings import YamlSettings
from heatmap import Heatmap

app = Flask(__name__)


# Route to display and handle the form
@app.route('/', methods=['GET', 'POST'])
def index():
    plot_url = None
    domain, start, end, group, title_period, side_title_period = (None,) * 6
    if request.method == 'POST':
        settings = YamlSettings(
            domain := request.form.get('domain'),
            start := request.form.get('start'),
            end := request.form.get('end'),
            group := 'M' if request.form.get('group') == 'monthly' else 'W',
            title_period := request.form.get('main_title_period'),
            side_title_period := request.form.get('side_title_period')
        )
        heatmap_obj = Heatmap(settings=settings)
        plot, fig = heatmap_obj.plt, heatmap_obj.fig
        img = BytesIO()
        fig.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        fig.clf()
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    return render_template('index.html', plot_url=plot_url, domain=domain,
                           start=start, end=end, group=group,
                           title_period=title_period,
                           side_title_period=side_title_period)


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
