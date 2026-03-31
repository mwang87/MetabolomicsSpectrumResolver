import ipaddress
import os

import flask
from flask import Flask
from flask_limiter import Limiter


APP_ROOT = os.path.dirname(os.path.realpath(__file__))

WHITELISTED_RANGES = [
    ipaddress.ip_network("138.23.0.0/16"),    # UCR
    ipaddress.ip_network("169.235.0.0/16"),    # UCR
    ipaddress.ip_network("132.239.0.0/16"),    # UCSD
    ipaddress.ip_network("137.110.0.0/16"),    # UCSD
    ipaddress.ip_network("192.31.146.0/24"),   # UCSD
]


def get_ip():
    if flask.request.headers.getlist("X-Forwarded-For"):
        ip = flask.request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = flask.request.remote_addr
    return ip.split(",")[0].strip()


def get_ip_or_exempt():
    try:
        client_ip = ipaddress.ip_address(get_ip())
        for network in WHITELISTED_RANGES:
            if client_ip in network:
                return "whitelisted-user"
    except ValueError:
        pass
    return get_ip()


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

limiter = Limiter(
    key_func=get_ip_or_exempt,
    app=app,
    default_limits=[],
    storage_uri="redis://metabolomicsusi-redis:6379",
)

# Import views after limiter is created to avoid circular import
from metabolomics_spectrum_resolver import views  # noqa: E402
app.register_blueprint(views.blueprint)
