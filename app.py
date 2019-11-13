import logging
import os

from flask import Flask

APP_ROOT = os.path.dirname(os.path.realpath(__file__))


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='(%',
        block_end_string='%)',
        variable_start_string='((',
        variable_end_string='))',
        comment_start_string='(#',
        comment_end_string='#)'))


app = CustomFlask(__name__)
app.config.from_object(__name__)

app.config['TEMPFOLDER'] = '/tmp'
try:
    os.mkdir(app.config['TEMPFOLDER'])
except FileExistsError:
    logging.warning('Cannot create %s', app.config['TEMPFOLDER'])
