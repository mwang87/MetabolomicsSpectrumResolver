import json
from urllib.parse import urlencode, quote, parse_qs
from typing import Any, Dict

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import requests
import werkzeug
from dash.dependencies import Input, Output, State

import views
from app import app


dash_app = dash.Dash(name='dashinterface', server=app,
                     url_base_pathname='/dashinterface/',
                     external_stylesheets=[dbc.themes.BOOTSTRAP])
dash_app.title = 'USI'

NAVBAR = dbc.Navbar(
    children=[
        dbc.NavbarBrand(html.Img(
            src='https://gnps-cytoscape.ucsd.edu/static/img/GNPS_logo.png',
            width='120px'), href='https://gnps.ucsd.edu'),
        dbc.Nav([dbc.NavItem(dbc.NavLink('Metabolomics USI - Dash Interface',
                                         href='#'))], navbar=True)],
    color='light', dark=False, sticky='top')

DATASELECTION_CARD = [
    dbc.CardHeader(html.H5('USI Data Selection')),
    dbc.CardBody([
        dbc.InputGroup([
            dbc.InputGroupAddon('Spectrum USI', addon_type='prepend'),
            dbc.Input(id='usi1', placeholder='Enter USI', value='')],
            className='mb-3'),
        html.Hr(),
        dbc.InputGroup(
            [dbc.InputGroupAddon('Spectrum USI', addon_type='prepend'),
             dbc.Input(id='usi2', placeholder='Enter USI', value='')],
            className='mb-3'),
        html.Hr(),
        dbc.Row([dbc.Col(html.H4('Drawing Controls')),
                 dbc.Col(html.A(dbc.Badge('Reset Figure', color='warning',
                                          className='mr-1'),
                                id='reset_figure'))]),
        html.Hr(),
        dbc.Row([dbc.Col('Figure Size'),
                 dbc.Col([dbc.InputGroup([
                     dbc.Input(id='width', type='number',
                               placeholder='input number', value=10,
                               step=0.01),
                     dbc.InputGroupAddon('\'', addon_type='append'),
                     html.Span(' X ', className='col-form-label'),
                     dbc.Input(id='height', type='number',
                               placeholder='input number', value=6,
                               step=0.01),
                     dbc.InputGroupAddon('\'', addon_type='append')])])]),
        html.Br(),
        dbc.Row([dbc.Col('Mass Range'),
                 dbc.Col([dbc.InputGroup([
                     dbc.Input(id='mz_min', type='number',
                               placeholder='min m/z'),
                     dbc.InputGroupAddon('m/z', addon_type='append'),
                     html.Span(' - ', className='col-form-label'),
                     dbc.Input(id='mz_max', type='number',
                               placeholder='max m/z'),
                     dbc.InputGroupAddon('m/z', addon_type='append')])])]),
        html.Br(),
        dbc.Row([dbc.Col('Maximum Intensity'),
                 dbc.Col([dbc.InputGroup([
                     dbc.Input(id='max_intensity', type='number',
                               placeholder='input number', value=125),
                     dbc.InputGroupAddon('%', addon_type='append')])])]),
        html.Br(),
        dbc.Row([dbc.Col('Label Precision'),
                 dbc.Col([dbc.Input(id='annotate_precision', type='number',
                                    placeholder='input number',
                                    value=4)])]),
        html.Br(),
        dbc.Row([dbc.Col('Label Rotation'),
                 dbc.Col([dbc.InputGroup([
                     dbc.Input(id='annotation_rotation', type='number',
                               placeholder='input number', value=90.0),
                     dbc.InputGroupAddon('°', addon_type='append')])])]),
        html.Br(),
        dbc.Row([dbc.Col('Cosine'),
                 dbc.Col([dbc.Select(
                     id='cosine', options=[
                         {'label': 'Standard', 'value': 'standard'},
                         {'label': 'Shifted', 'value': 'shifted'}],
                     value='standard')])]),
        html.Br(),
        dbc.Row([dbc.Col('Fragment tolerance'),
                 dbc.Col([dbc.InputGroup([
                     dbc.Input(
                         id='fragment_mz_tolerance', type='number',
                         placeholder='input number', value=0.1,
                         step='any'),
                     dbc.InputGroupAddon('m/z', addon_type='append')])])]),
        html.Br(),
        dbc.Row([dbc.Col('Show Grid'),
                 dbc.Col([
                     dcc.Dropdown(
                         id='grid', options=[
                             {'label': 'Yes', 'value': 'true'},
                             {'label': 'No', 'value': 'false'}],
                         value='true', clearable=False)])]),
        html.Br(),
        html.H4('UI Adjustment'),
        html.Hr(),
        dbc.Row([dbc.Col('Selection Size'),
                 dbc.Col([dcc.Slider(id='ui_width', min=2, max=6, value=4,
                                     marks={2: {'label': '2'},
                                            4: {'label': '4'},
                                            6: {'label': '6'}},
                                     included=True)])])])
]

LEFT_DASHBOARD = [html.Div([html.Div(DATASELECTION_CARD)])]

MIDDLE_DASHBOARD = [
    dbc.CardHeader(html.H5('Data Visualization')),
    dbc.CardBody([
        dcc.Loading(id='output',
                    children=[html.Div([html.Div(id='loading-output-23')])],
                    type='default'),
        dbc.Row([
            dbc.Col(dash_table.DataTable(
                id='peak_table1', columns=[{'name': 'filename',
                                            'id': 'filename'}],
                data=[], page_size=10, sort_action='native',
                row_selectable='multi', filter_action='native',
                selected_rows=[])),
            dbc.Col(dash_table.DataTable(
                id='peak_table2', columns=[{'name': 'filename',
                                            'id': 'filename'}],
                data=[], page_size=10, sort_action='native',
                row_selectable='multi', filter_action='native',
                selected_rows=[]))])])
]

CONTRIBUTORS_DASHBOARD = [
    dbc.CardHeader(html.H5('Contributors')),
    dbc.CardBody(['Mingxun Wang PhD - UC San Diego',
                  html.Br(),
                  'Wout Bittremieux PhD - UC San Diego',
                  html.Br(),
                  'Christopher Chen - UC San Diego',
                  html.Br(),
                  'Simon Rogers PhD - University of Glasgow',
                  html.Br(),
                  html.Br(),
                  html.H5('Citation'),
                  html.A('Bittremieux, Wout, Christopher Chen, Pieter C. '
                         'Dorrestein, Emma L. Schymanski, Tobias Schulze, '
                         'Steffen Neumann, Rene Meier, Simon Rogers, and '
                         'Mingxun Wang. "Universal MS / MS Visualization and '
                         'Retrieval with the Metabolomics Spectrum Resolver '
                         'Web Service." bioRxiv (2020).',
                         href='https://www.biorxiv.org/content/'
                              '10.1101/2020.05.09.086066v1')])
]

EXAMPLES_DASHBOARD = [
    dbc.CardHeader(html.H5('Examples')),
    dbc.CardBody([html.A('Basic', href='/dashinterface/'),
                  html.Br(),
                  html.A('Proteomics',
                         href='/dashinterface/?usi1=mzspec%3A'
                              'PXD002854%3A'
                              '20150414_QEp1_LC7_GaPI_SA_Serum_LH_30.mzXML%3A'
                              'scan%3A15073%3AHPYFYAPELLFFAKR%2F3'),
                  dcc.Loading(
                      id='debug',
                      children=[html.Div([html.Div(id='loading-output-243')])],
                      type='default')])
]

BODY = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dbc.Row([dbc.Col([dbc.Card(LEFT_DASHBOARD)], className='col-4',
                     id='left_panel_col'),
             dbc.Col([dbc.Card(MIDDLE_DASHBOARD),
                      html.Br(),
                      dbc.Card(CONTRIBUTORS_DASHBOARD),
                      html.Br(),
                      dbc.Card(EXAMPLES_DASHBOARD)],
                     className='col-8', id='right_panel_col')],
            style={'marginTop': 30})],
    fluid=True, className='',
)

dash_app.layout = html.Div(children=[NAVBAR, BODY])


def _get_url_param(param_dict: Dict, key: str, default: Any):
    return param_dict.get(key, [default])[0]


@dash_app.callback(
    [
        Output('usi1', 'value'),
        Output('usi2', 'value'),
        Output('width', 'value'),
        Output('height', 'value'),
        Output('mz_min', 'value'),
        Output('mz_max', 'value'),
        Output('max_intensity', 'value'),
        Output('annotate_precision', 'value'),
        Output('annotation_rotation', 'value'),
        Output('cosine', 'value'),
        Output('fragment_mz_tolerance', 'value'),
        Output('grid', 'value')
    ],
    [
        Input('url', 'pathname')
    ],
    [
        State('url', 'search')
    ])
def determine_task(pathname, search):
    """
    TODO

    Parameters
    ----------
    pathname :
    search :

    Returns
    -------

    """
    try:
        query_dict = parse_qs(search[1:])
    except:     # FIXME
        query_dict = {}

    usi1 = _get_url_param(query_dict, 'usi1', _get_url_param(
        query_dict, 'usi', 'mzspec:MSV000082796:KP_108_Positive:scan:1974'))
    usi2 = _get_url_param(query_dict, 'usi2', dash.no_update)

    width = _get_url_param(query_dict, 'width', dash.no_update)
    height = _get_url_param(query_dict, 'height', dash.no_update)
    mz_min = _get_url_param(query_dict, 'mz_min', dash.no_update)
    mz_max = _get_url_param(query_dict, 'mz_max', dash.no_update)

    max_intensity = _get_url_param(query_dict, 'max_intensity', dash.no_update)
    annotate_precision = _get_url_param(query_dict, 'annotate_precision',
                                        dash.no_update)
    annotation_rotation = _get_url_param(query_dict, 'annotation_rotation',
                                         dash.no_update)
    cosine = _get_url_param(query_dict, 'cosine', dash.no_update)
    fragment_mz_tolerance = _get_url_param(query_dict, 'fragment_mz_tolerance',
                                           dash.no_update)
    grid = _get_url_param(query_dict, 'grid', dash.no_update)

    return (usi1, usi2, width, height, mz_min, mz_max, max_intensity,
            annotate_precision, annotation_rotation, cosine,
            fragment_mz_tolerance, grid)


def _process_single_usi(usi, plotting_args):
    """
    TODO

    Parameters
    ----------
    usi :
    plotting_args :

    Returns
    -------

    """
    spectrum, source_link, splash_key = views._parse_usi(usi)
    cleaned_plotting_args = views._get_plotting_args(
        werkzeug.datastructures.ImmutableMultiDict(plotting_args))
    spectrum = views._prepare_spectrum(spectrum, **cleaned_plotting_args)

    usi1_url = f'/svg/?{urlencode(plotting_args, quote_via=quote)}'
    local_url = f'http://localhost:5000{usi1_url}'
    r = requests.get(local_url)     # TODO: What happens with `r`?

    image_obj = html.Img(src=usi1_url)

    json_button = html.A(
        dbc.Button('Download as JSON', color='primary', className='mr-1'),
        href=f'/json/?usi={quote(usi)}')
    csv_button = html.A(
        dbc.Button('Download as CSV', color='primary', className='mr-1'),
        href=f'/csv/?usi={quote(usi)}')
    png_button = html.A(
        dbc.Button('Download as PNG', color='primary', className='mr-1'),
        href=f'/png/?{urlencode(plotting_args, quote_via=quote)}',
        download='spectrum.png')
    svg_button = html.A(
        dbc.Button('Download as SVG', color='primary', className='mr-1'),
        href=usi1_url, download='spectrum.svg')
    download_div = dbc.Row([
        dbc.Col([html.Img(src='/qrcode?usi={}'.format(quote(usi)))],
                className='col-1'),
        dbc.Col([
            dbc.Row([dbc.Col('Universal Spectrum Identifier',
                                  className='col-3 font-weight-bold text-right'),
                          dbc.Col([usi, ' ',
                                   html.A(dbc.Badge('Source', color='info',
                                                    className='mr-1'),
                                          href=source_link)],
                                  className='col-8')]),
            dbc.Row([dbc.Col('SPLASH Identifier',
                             className='col-3 font-weight-bold text-right'),
                     dbc.Col(splash_key, className='col-8')]),
            dbc.Row([json_button, csv_button, png_button, svg_button],
                    className='offset-1')],
            className='col-11')
    ])

    # FIXME
    peak_annotations = spectrum.annotation.nonzero()[0].tolist()
    peaks_list = views._get_peaks(spectrum)

    return (download_div, image_obj), plotting_args


def _process_single_usi_table(usi, plotting_args):
    """
    TODO

    Parameters
    ----------
    usi :
    plotting_args :

    Returns
    -------

    """
    spectrum, source_link, splash_key = views._parse_usi(usi)
    cleaned_plotting_args = views._get_plotting_args(
        werkzeug.datastructures.ImmutableMultiDict(plotting_args))
    spectrum = views._prepare_spectrum(spectrum, **cleaned_plotting_args)

    peak_annotations_indices = spectrum.annotation.nonzero()[0].tolist()
    peaks_list = views._get_peaks(spectrum)

    # Create a table of peak annotations.
    peaks_df = pd.DataFrame({'mz': [peak[0] for peak in peaks_list],
                             'i': [peak[1] for peak in peaks_list]})
    columns = [{'name': column, 'id': column} for column in peaks_df.columns]

    return (peaks_df.to_dict(orient='records'), columns,
            peak_annotations_indices)


def _process_mirror_usi(usi1, usi2, plotting_args):
    """
    TODO

    Parameters
    ----------
    usi1 :
    usi2 :
    plotting_args :

    Returns
    -------

    """
    spectrum1, source_link1, splash_key1 = views._parse_usi(usi1)
    spectrum2, source_link2, splash_key2 = views._parse_usi(usi2)
    cleaned_plotting_args = views._get_plotting_args(
        werkzeug.datastructures.ImmutableMultiDict(plotting_args), mirror=True)
    # FIXME
    spectrum1, spectrum2 = views._prepare_mirror_spectra(spectrum1, spectrum2,
                                                         cleaned_plotting_args)

    mirror_url = f'/svg/mirror/?{urlencode(plotting_args, quote_via=quote)}'
    local_url = f'http://localhost:5000{mirror_url}'
    r = requests.get(local_url)     # FIXME

    image_obj = html.Img(src=mirror_url)

    json_button = html.A(
        dbc.Button('Download as JSON', color='primary', className='mr-1'),
        href=f'/json/mirror?usi1={quote(usi1)}&usi2={quote(usi2)}')
    png_button = html.A(
        dbc.Button('Download as PNG', color='primary', className='mr-1'),
        href=f'/png/mirror?usi1={quote(usi1)}&usi2={quote(usi2)}',
        download='mirror.png')
    svg_button = html.A(
        dbc.Button('Download as SVG', color='primary', className='mr-1'),
        href=mirror_url, download='mirror.svg')
    download_div = dbc.Row([
        dbc.Col([
            html.Img(src=f'/qrcode?mirror=true&usi1={quote(usi1)}&'
                         f'usi2={quote(usi2)}')],
            className='col-1'),
        dbc.Col([
            dbc.Row([
                dbc.Col('Universal Spectrum Identifier 1',
                        className='col-4 font-weight-bold text-right'),
                dbc.Col([usi1, ' ', html.A(
                    dbc.Badge('Source', color='info', className='mr-1'),
                    href=source_link1)], className='col-8')]),
            dbc.Row([
                dbc.Col('SPLASH Identifier 1',
                        className='col-4 font-weight-bold text-right'),
                dbc.Col(splash_key1, className='col-8')]),
            dbc.Row([
                dbc.Col('Universal Spectrum Identifier 2',
                        className='col-4 font-weight-bold text-right'),
                dbc.Col([usi2, ' ', html.A(
                    dbc.Badge('Source', color='info', className='mr-1'),
                    href=source_link2)], className='col-8')]),
            dbc.Row([
                dbc.Col('SPLASH Identifier 2',
                        className='col-4 font-weight-bold text-right'),
                dbc.Col(splash_key2, className='col-8')]),
            dbc.Row([json_button, png_button, svg_button],
                    className='offset-2'),],
            className='col-11')
    ])

    return (download_div, image_obj, html.Br()), plotting_args


@dash_app.callback(
    [
        Output('output', 'children'),
        Output('url', 'search'),
        Output('debug', 'children'),
    ],
    [
        Input('usi1', 'value'),
        Input('usi2', 'value'),
        Input('width', 'value'),
        Input('height', 'value'),
        Input('mz_min', 'value'),
        Input('mz_max', 'value'),
        Input('max_intensity', 'value'),
        Input('annotate_precision', 'value'),
        Input('annotation_rotation', 'value'),
        Input('cosine', 'value'),
        Input('fragment_mz_tolerance', 'value'),
        Input('grid', 'value'),
        Input('peak_table1', 'derived_virtual_data'),
        Input('peak_table1', 'derived_virtual_selected_rows'),
        Input('peak_table2', 'derived_virtual_data'),
        Input('peak_table2', 'derived_virtual_selected_rows'),
    ],
    [
    ])
def draw_figure(usi1, usi2,
                width,
                height,
                mz_min,
                mz_max,
                max_intensity,
                annotate_precision,
                annotation_rotation,
                cosine,
                fragment_mz_tolerance,
                grid,
                derived_virtual_data,
                derived_virtual_selected_rows,
                derived_virtual_data2,
                derived_virtual_selected_rows2):
    """
    TODO

    Parameters
    ----------
    usi1 :
    usi2 :
    width :
    height :
    mz_min :
    mz_max :
    max_intensity :
    annotate_precision :
    annotation_rotation :
    cosine :
    fragment_mz_tolerance :
    grid :
    derived_virtual_data :
    derived_virtual_selected_rows :
    derived_virtual_data2 :
    derived_virtual_selected_rows2 :

    Returns
    -------

    """
    plotting_args = {'width': width, 'height': height, 'cosine': cosine,
                     'grid': grid}

    # FIXME
    try:
        plotting_args['mz_min'] = float(mz_min)
    except:
        pass
    try:
        plotting_args['mz_max'] = float(mz_max)
    except:
        pass
    try:
        plotting_args['max_intensity'] = float(max_intensity)
    except:
        pass
    try:
        plotting_args['annotate_precision'] = int(annotate_precision)
    except:
        pass
    try:
        plotting_args['annotation_rotation'] = float(annotation_rotation)
    except:
        pass
    try:
        plotting_args['fragment_mz_tolerance'] = float(fragment_mz_tolerance)
    except:
        pass

    if len(usi1) > 0 and len(usi2) > 0:
        # Mirror spectrum.
        plotting_args['usi1'] = usi1
        plotting_args['usi2'] = usi2

        annotation_masses = []
        if derived_virtual_selected_rows is not None:
            for selected_index in derived_virtual_selected_rows:
                annotation_masses.append(
                    derived_virtual_data[selected_index]['mz'])

        annotation_masses2 = []
        if derived_virtual_selected_rows2 is not None:
            for selected_index in derived_virtual_selected_rows2:
                annotation_masses2.append(
                    derived_virtual_data2[selected_index]['mz'])

        plotting_args['annotate_peaks'] = json.dumps(
            [annotation_masses, annotation_masses2])
        spectrum_visualization, plotting_args = _process_mirror_usi(
            usi1, usi2, plotting_args)

        return (spectrum_visualization,
                f'?{urlencode(plotting_args, quote_via=quote)}',
                '')
    else:
        # Single spectrum.
        plotting_args['usi'] = usi1

        annotation_masses = []
        if derived_virtual_selected_rows is not None:
            for selected_index in derived_virtual_selected_rows:
                annotation_masses.append(
                    derived_virtual_data[selected_index]['mz'])

        plotting_args['annotate_peaks'] = json.dumps([annotation_masses])
        spectrum_visualization, plotting_args = _process_single_usi(
            usi1, plotting_args)
        plotting_args['usi1'] = usi1

        return (spectrum_visualization,
                f'?{urlencode(plotting_args, quote_via=quote)}',
                '')


@dash_app.callback(
    [
        Output('peak_table1', 'data'),
        Output('peak_table1', 'columns'),
        Output('peak_table1', 'selected_rows'),
        Output('peak_table2', 'data'),
        Output('peak_table2', 'columns'),
        Output('peak_table2', 'selected_rows'),
    ],
    [
        Input('usi1', 'value'),
        Input('usi2', 'value'),
        Input('url', 'pathname')
    ],
    [
        State('url', 'search')
    ])
def draw_table(usi1, usi2, pathname, search):
    """
    TODO

    Parameters
    ----------
    usi1 :
    usi2 :
    pathname :
    search :

    Returns
    -------

    """
    plotting_args = {}

    # Determine URL override.
    triggered_ids = [p['prop_id'] for p in dash.callback_context.triggered]
    if 'url.pathname' in triggered_ids:
        # Doing override from URL for selected rows.
        try:
            query_dict = parse_qs(search[1:])
        except:     # FIXME
            query_dict = {}

        try:
            plotting_args['annotate_peaks'] = _get_url_param(
                query_dict, 'annotate_peaks', None)
            plotting_args['fragment_mz_tolerance'] = float(
                _get_url_param(query_dict, 'fragment_mz_tolerance', 0.02))
            if plotting_args['annotate_peaks'] is None:
                plotting_args = {}
        except:     # FIXME
            pass

    # Setting up parameters from url
    if len(usi1) > 0 and len(usi2) > 0:
        peaks1, columns1, selected_rows1 = _process_single_usi_table(
            usi1, plotting_args)
        peaks2, columns2, selected_rows2 = _process_single_usi_table(
            usi2, plotting_args)
    else:
        peaks1, columns1, selected_rows1 = _process_single_usi_table(
            usi1, plotting_args)
        peaks2, columns2, selected_rows2 = [], dash.no_update, []

    return peaks1, columns1, selected_rows1, peaks2, columns2, selected_rows2


@dash_app.callback(
    [
        Output('left_panel_col', 'className'),
        Output('right_panel_col', 'className'),
    ],
    [
        Input('ui_width', 'value'),
    ],
    [
    ])
def set_ui_width(ui_width):
    """
    TODO

    Parameters
    ----------
    ui_width :

    Returns
    -------

    """
    return f'col-{ui_width}', f'col-{12 - ui_width}'


@dash_app.callback(
    [
        Output('reset_figure', 'href'),
    ],
    [
        Input('usi1', 'value'),
        Input('usi2', 'value'),
    ],
    [
    ])
def create_reset(usi1, usi2):
    """
    TODO

    Parameters
    ----------
    usi1 :
    usi2 :

    Returns
    -------

    """
    if len(usi1) > 0 and len(usi2) > 0:
        return [f'/dashinterface/?usi1={quote(usi1)}&usi2={quote(usi2)}']
    else:
        return [f'/dashinterface/?usi={quote(usi1)}']


if __name__ == '__main__':
    # TODO: Disable debug.
    dash_app.run_server(host='0.0.0.0', port=5000, debug=True)
