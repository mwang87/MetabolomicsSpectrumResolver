import ipaddress

import flask
from flask_limiter import Limiter

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


def is_whitelisted():
    try:
        client_ip = ipaddress.ip_address(get_ip())
        for network in WHITELISTED_RANGES:
            if client_ip in network:
                return True
    except ValueError:
        pass
    return False


limiter = Limiter(
    key_func=get_ip,
    default_limits=[],
    storage_uri="redis://metabolomicsusi-redis:6379",
    request_identifier=get_ip,
)


@limiter.request_filter
def whitelist_filter():
    return is_whitelisted()
