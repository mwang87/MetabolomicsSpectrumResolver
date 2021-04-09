import dash
import dash_core_components as dcc
import dash_html_components as html

from app import app

dash_app = dash.Dash(name='dashinterface', 
                server=app, url_base_pathname='/dashinterface/')

dash_app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),
])