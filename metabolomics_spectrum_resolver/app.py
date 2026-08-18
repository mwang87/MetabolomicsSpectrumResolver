import os

from flask import Flask
from flask_cors import CORS

from metabolomics_spectrum_resolver import views
from metabolomics_spectrum_resolver.rate_limit import limiter


APP_ROOT = os.path.dirname(os.path.realpath(__file__))


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(
        dict(
            block_start_string="(%",
            block_end_string="%)",
            variable_start_string="((",
            variable_end_string="))",
            comment_start_string="(#",
            comment_end_string="#)",
        )
    )


app = CustomFlask(__name__)
app.config.from_object(__name__)
# Allow cross-origin requests from gnps2.org and any of its subdomains.
CORS(app, origins=[r"https?://(.*\.)?gnps2\.org$"])
limiter.init_app(app)
app.register_blueprint(views.blueprint)
