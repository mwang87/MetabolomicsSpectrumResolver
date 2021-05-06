import json
from urllib.parse import urlencode, quote, parse_qs
from typing import Any, Dict, List, Tuple, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import requests
import werkzeug
from dash.dependencies import Input, Output, State

import views
from app import app


defaults = {
    "example_usi": "mzspec:MSV000082796:KP_108_Positive:scan:1974",
    "fragment_mz_tolerance": 0.02,
}


dash_app = dash.Dash(
    name="dashinterface",
    server=app,
    url_base_pathname="/dashinterface/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
dash_app.title = "USI"

NAVBAR = dbc.Navbar(
    children=[
        dbc.NavbarBrand(
            html.Img(
                src="https://gnps-cytoscape.ucsd.edu/static/img/GNPS_logo.png",
                width="120px",
            ),
            href="https://gnps.ucsd.edu",
        ),
        dbc.Nav(
            [
                dbc.NavItem(
                    dbc.NavLink("Metabolomics USI — Dash Interface", href="#")
                )
            ],
            navbar=True,
        ),
    ],
    color="light",
    dark=False,
    sticky="top",
)

DATASELECTION_CARD = [
    dbc.CardHeader(html.H5("USI Data Selection")),
    dbc.CardBody(
        [
            dbc.InputGroup(
                [
                    dbc.InputGroupAddon("Spectrum USI", addon_type="prepend"),
                    dbc.Input(id="usi1", placeholder="Enter USI", value=""),
                ],
                className="mb-3",
            ),
            html.Hr(),
            dbc.InputGroup(
                [
                    dbc.InputGroupAddon("Spectrum USI", addon_type="prepend"),
                    dbc.Input(
                        id="usi2",
                        placeholder="Enter USI (optional; for mirror plots)",
                        value="",
                    ),
                ],
                className="mb-3",
            ),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col(html.H4("Drawing Controls")),
                    dbc.Col(
                        html.A(
                            dbc.Badge(
                                "Reset Figure",
                                color="warning",
                                className="mr-1",
                            ),
                            id="reset_figure",
                        )
                    ),
                ]
            ),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col("Figure Size"),
                    dbc.Col(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="width",
                                        max=100,
                                        min=1,
                                        placeholder="input number",
                                        step=0.01,
                                        type="number",
                                        value=10,
                                    ),
                                    dbc.InputGroupAddon(
                                        "in", addon_type="append"
                                    ),
                                    html.Span(
                                        " X ", className="col-form-label"
                                    ),
                                    dbc.Input(
                                        id="height",
                                        max=100,
                                        min=1,
                                        placeholder="input number",
                                        step=0.01,
                                        value=6,
                                        type="number",
                                    ),
                                    dbc.InputGroupAddon(
                                        "in", addon_type="append"
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Mass Range"),
                    dbc.Col(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="mz_min",
                                        min=0,
                                        placeholder="min m/z",
                                        type="number",
                                    ),
                                    dbc.InputGroupAddon(
                                        "m/z", addon_type="append"
                                    ),
                                    html.Span(
                                        " - ", className="col-form-label"
                                    ),
                                    dbc.Input(
                                        id="mz_max",
                                        min=0,
                                        placeholder="max m/z",
                                        type="number",
                                    ),
                                    dbc.InputGroupAddon(
                                        "m/z", addon_type="append"
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Maximum Intensity"),
                    dbc.Col(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="max_intensity",
                                        min=0,
                                        placeholder="input number",
                                        value=125,
                                        type="number",
                                    ),
                                    dbc.InputGroupAddon(
                                        "%", addon_type="append"
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Label Precision"),
                    dbc.Col(
                        [
                            dbc.Input(
                                id="annotate_precision",
                                min=0,
                                placeholder="input number",
                                value=4,
                                type="number",
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Label Rotation"),
                    dbc.Col(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="annotation_rotation",
                                        max=360,
                                        min=0,
                                        placeholder="input number",
                                        value=90.0,
                                        type="number",
                                    ),
                                    dbc.InputGroupAddon(
                                        "°", addon_type="append"
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Cosine"),
                    dbc.Col(
                        [
                            dbc.Select(
                                id="cosine",
                                options=[
                                    {"label": "Standard", "value": "standard"},
                                    {"label": "Shifted", "value": "shifted"},
                                ],
                                value="standard",
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Fragment Tolerance"),
                    dbc.Col(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="fragment_mz_tolerance",
                                        min=0,
                                        placeholder="input number",
                                        step="any",
                                        value=0.1,
                                        type="number",
                                    ),
                                    dbc.InputGroupAddon(
                                        "m/z", addon_type="append"
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col("Show Grid"),
                    dbc.Col(
                        [
                            dcc.Dropdown(
                                id="grid",
                                options=[
                                    {"label": "Yes", "value": "true"},
                                    {"label": "No", "value": "false"},
                                ],
                                value="true",
                                clearable=False,
                            )
                        ]
                    ),
                ]
            ),
            html.Br(),
            html.H4("UI Adjustment"),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col("Selection Size"),
                    dbc.Col(
                        [
                            dcc.Slider(
                                id="ui_width",
                                included=True,
                                marks={
                                    2: {"label": "2"},
                                    4: {"label": "4"},
                                    6: {"label": "6"},
                                },
                                max=6,
                                min=2,
                                value=4,
                            )
                        ]
                    ),
                ]
            ),
        ]
    ),
]

LEFT_DASHBOARD = [html.Div([html.Div(DATASELECTION_CARD)])]

MIDDLE_DASHBOARD = [
    dbc.CardHeader(html.H5("Data Visualization")),
    dbc.CardBody(
        [
            dcc.Loading(
                id="output",
                children=[html.Div([html.Div(id="loading-output-23")])],
                type="default",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dash_table.DataTable(
                            id="peak_table1",
                            columns=[{"name": "filename", "id": "filename"}],
                            data=[],
                            filter_action="native",
                            page_size=10,
                            row_selectable="multi",
                            selected_rows=[],
                            sort_action="native",
                        )
                    ),
                    dbc.Col(
                        dash_table.DataTable(
                            id="peak_table2",
                            columns=[{"name": "filename", "id": "filename"}],
                            data=[],
                            filter_action="native",
                            page_size=10,
                            row_selectable="multi",
                            selected_rows=[],
                            sort_action="native",
                        )
                    ),
                ]
            ),
        ]
    ),
]

CONTRIBUTORS_DASHBOARD = [
    dbc.CardHeader(html.H5("Contributors")),
    dbc.CardBody(
        [
            "Mingxun Wang, PhD – UC San Diego",
            html.Br(),
            "Wout Bittremieux, PhD – UC San Diego",
            html.Br(),
            "Christopher Chen – UC San Diego",
            html.Br(),
            "Simon Rogers, PhD – University of Glasgow",
            html.Br(),
            html.Br(),
            html.H5("Citation"),
            html.A(
                "Bittremieux, Wout, Christopher Chen, Pieter C. Dorrestein, "
                "Emma L. Schymanski, Tobias Schulze, Steffen Neumann, Rene "
                'Meier, Simon Rogers, and Mingxun Wang. "Universal MS/MS '
                "Visualization and Retrieval with the Metabolomics Spectrum "
                'Resolver Web Service." bioRxiv (2020).',
                href="https://doi.org/10.1101/2020.05.09.086066",
            ),
        ]
    ),
]

EXAMPLES_DASHBOARD = [
    dbc.CardHeader(html.H5("Examples")),
    dbc.CardBody(
        [
            html.A("Basic", href="/dashinterface/"),
            html.Br(),
            html.A(
                "Proteomics",
                href=(
                    "/dashinterface/?usi1=mzspec%3APXD002854%3A"
                    "20150414_QEp1_LC7_GaPI_SA_Serum_LH_30.mzXML%3A"
                    "scan%3A15073%3AHPYFYAPELLFFAKR%2F3"
                ),
            ),
            dcc.Loading(
                id="debug",
                children=[html.Div([html.Div(id="loading-output-243")])],
                type="default",
            ),
        ]
    ),
]

BODY = dbc.Container(
    [
        dcc.Location(id="url", refresh=False),
        dbc.Row(
            [
                dbc.Col(
                    [dbc.Card(LEFT_DASHBOARD)],
                    className="col-4",
                    id="left_panel_col",
                ),
                dbc.Col(
                    [
                        dbc.Card(MIDDLE_DASHBOARD),
                        html.Br(),
                        dbc.Card(CONTRIBUTORS_DASHBOARD),
                        html.Br(),
                        dbc.Card(EXAMPLES_DASHBOARD),
                    ],
                    className="col-8",
                    id="right_panel_col",
                ),
            ],
            style={"marginTop": 30},
        ),
    ],
    fluid=True,
    className="",
)

dash_app.layout = html.Div(children=[NAVBAR, BODY])


def _get_url_param(
    param_dict: Dict[str, List[str]], key: str, default: Any = None
) -> Any:
    """
    Utitility function to extract parameters from a URL dictionary.

    Parameters
    ----------
    param_dict : Dict[str, List[str]]
        A URL parameter dictionary consisting of the parameter keys and a list
        of their values (expected to only contain a single value).
    key : str
        The parameter to retrieve.
    default : Any
        A default value in case `param_dict` does not contain `key`.

    Returns
    -------
    Any
        The first value in the list for `key` in `param_dict`, or `default` if
        `param_dict` does not contain `key`.
    """
    return param_dict[key][0] if key in param_dict else default


@dash_app.callback(
    [
        Output("usi1", "value"),
        Output("usi2", "value"),
        Output("width", "value"),
        Output("height", "value"),
        Output("mz_min", "value"),
        Output("mz_max", "value"),
        Output("max_intensity", "value"),
        Output("annotate_precision", "value"),
        Output("annotation_rotation", "value"),
        Output("cosine", "value"),
        Output("fragment_mz_tolerance", "value"),
        Output("grid", "value"),
    ],
    [Input("url", "pathname")],
    [State("url", "search")],
)
def determine_task(
    pathname: str, search: str
) -> Tuple[
    str,
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
    Union[str, dash.no_update],
]:
    """
    Apply URL parameters to the settings.

    Parameters
    ----------
    pathname : str
        URL path.
    search : str
        URL-encoded parameter string.

    Returns
    -------
    Tuple[str,
          Union[str, dash.no_update], Union[str, dash.no_update],
          Union[str, dash.no_update], Union[str, dash.no_update],
          Union[str, dash.no_update], Union[str, dash.no_update],
          Union[str, dash.no_update], Union[str, dash.no_update],
          Union[str, dash.no_update], Union[str, dash.no_update],
          Union[str, dash.no_update]
    ]
        The (string encoded) values for:
        - The first USI.
        - The second USI.
        - The figure width.
        - The figure height.
        - The minimum m/z value.
        - The maximum m/z value.
        - The maximum intensity value.
        - The m/z precision for peak annotations.
        - The angle of peak annotations.
        - The type of cosine score to compute.
        - The fragment m/z tolerance.
        - Whether to use a grid.
    """
    args_dict = parse_qs(search[1:])
    usi1 = _get_url_param(
        args_dict,
        "usi1",
        _get_url_param(args_dict, "usi", defaults["example_usi"]),
    )
    usi2 = _get_url_param(args_dict, "usi2", dash.no_update)

    width = _get_url_param(args_dict, "width", dash.no_update)
    height = _get_url_param(args_dict, "height", dash.no_update)
    mz_min = _get_url_param(args_dict, "mz_min", dash.no_update)
    mz_max = _get_url_param(args_dict, "mz_max", dash.no_update)
    max_intensity = _get_url_param(args_dict, "max_intensity", dash.no_update)
    annotate_precision = _get_url_param(
        args_dict, "annotate_precision", dash.no_update
    )
    annotation_rotation = _get_url_param(
        args_dict, "annotation_rotation", dash.no_update
    )
    cosine = _get_url_param(args_dict, "cosine", dash.no_update)
    fragment_mz_tolerance = _get_url_param(
        args_dict, "fragment_mz_tolerance", dash.no_update
    )
    grid = _get_url_param(args_dict, "grid", dash.no_update)

    return (
        usi1,
        usi2,
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
    )


def _process_single_usi(
    usi: str, plotting_args: Dict[str, Any]
) -> Tuple[Any, Dict[str, Any]]:
    """
    Process the given USI for plotting.

    Parameters
    ----------
    usi : str
        The USI to process.
    plotting_args : Dict[str, Any]
        The parameters to plot the USI's spectrum.

    Returns
    -------
    Tuple[Any, Dict[str, Any]]
        A tuple with a tuple of the HTML div to download resources associated
        with the given USI and its image, and the plotting parameters.
    """
    _, source_link, splash_key = views.parse_usi(usi)
    plotting_args = views.get_plotting_args(
        werkzeug.datastructures.ImmutableMultiDict(plotting_args)
    )

    usi_url = f"/svg/?{urlencode(plotting_args, quote_via=quote)}"
    # This attempts to create the image to warm the cache.
    requests.get(f"http://localhost:5000{usi_url}")

    image_obj = html.Img(src=usi_url)

    json_button = html.A(
        dbc.Button("Download as JSON", color="primary", className="mr-1"),
        href=f"/json/?usi={quote(usi)}",
    )
    csv_button = html.A(
        dbc.Button("Download as CSV", color="primary", className="mr-1"),
        href=f"/csv/?usi={quote(usi)}",
    )
    png_button = html.A(
        dbc.Button("Download as PNG", color="primary", className="mr-1"),
        href=f"/png/?{urlencode(plotting_args, quote_via=quote)}",
        download="spectrum.png",
    )
    svg_button = html.A(
        dbc.Button("Download as SVG", color="primary", className="mr-1"),
        href=usi_url,
        download="spectrum.svg",
    )
    download_div = dbc.Row(
        [
            dbc.Col(
                [html.Img(src=f"/qrcode?usi={quote(usi)}")], className="col-1",
            ),
            dbc.Col(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                "Universal Spectrum Identifier",
                                className="col-3 font-weight-bold text-right",
                            ),
                            dbc.Col(
                                [
                                    usi,
                                    " ",
                                    html.A(
                                        dbc.Badge(
                                            "Source",
                                            color="info",
                                            className="mr-1",
                                        ),
                                        href=source_link,
                                    ),
                                ],
                                className="col-8",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                "SPLASH Identifier",
                                className="col-3 font-weight-bold text-right",
                            ),
                            dbc.Col(splash_key, className="col-8"),
                        ]
                    ),
                    dbc.Row(
                        [json_button, csv_button, png_button, svg_button],
                        className="offset-1",
                    ),
                ],
                className="col-11",
            ),
        ]
    )

    return (download_div, image_obj), plotting_args


def _process_single_usi_table(
    usi: str, plotting_args: Dict[str, Any]
) -> Tuple[List[Dict[str, float]], List[Dict[str, str]], List[int]]:
    """
    Process the given USI to generate a peak table.

    Parameters
    ----------
    usi : str
        The USI to process.
    plotting_args : Dict[str, Any]
        The parameters to plot the USI's spectrum.

    Returns
    -------
    Tuple[List[Dict[str, float]], List[Dict[str, str]], List[int]]
        (i) The spectrum's peaks as a dictionary of "m/z" and "Intensity"
        values; (ii) a dictionary of the column labels; (iii) a list with
        peak indexes.
    """
    spectrum, source_link, splash_key = views.parse_usi(usi)
    plotting_args = views.get_plotting_args(
        werkzeug.datastructures.ImmutableMultiDict(plotting_args)
    )
    spectrum = views.prepare_spectrum(spectrum, **plotting_args)

    peaks = [
        {"m/z": peak[0], "Intensity": peak[1]}
        for peak in views.get_peaks(spectrum)
    ]
    columns = [
        {"name": "m/z", "id": "m/z"},
        {"name": "Intensity", "id": "Intensity"},
    ]
    peak_annotations_indices = spectrum.annotation.nonzero()[0].tolist()

    return peaks, columns, peak_annotations_indices


def _process_mirror_usi(
    usi1: str, usi2: str, plotting_args: Dict[str, Any]
) -> Tuple[Any, Dict[str, Any]]:
    """
    Process the given USIs for plotting in a mirror plot.

    Parameters
    ----------
    usi1 : str
        The first USI to process.
    usi2 : str
        The second USI to process.
    plotting_args : Dict[str, Any]
        The parameters to create the mirror plot.

    Returns
    -------
    Tuple[Any, Dict[str, Any]]
        A tuple with a tuple of the HTML div to download resources associated
        with the given USIs and their mirror plot, and the plotting parameters.
    """
    _, source_link1, splash_key1 = views.parse_usi(usi1)
    _, source_link2, splash_key2 = views.parse_usi(usi2)
    plotting_args = views.get_plotting_args(
        werkzeug.datastructures.ImmutableMultiDict(plotting_args), mirror=True
    )

    mirror_url = f"/svg/mirror/?{urlencode(plotting_args, quote_via=quote)}"
    local_url = f"http://localhost:5000{mirror_url}"
    # This attempts to create the image to warm the cache.
    requests.get(local_url)

    image_obj = html.Img(src=mirror_url)

    json_button = html.A(
        dbc.Button("Download as JSON", color="primary", className="mr-1"),
        href=f"/json/mirror?{urlencode(plotting_args, quote_via=quote)}",
    )
    png_button = html.A(
        dbc.Button("Download as PNG", color="primary", className="mr-1"),
        href=f"/png/mirror?{urlencode(plotting_args, quote_via=quote)}",
        download="mirror.png",
    )
    svg_button = html.A(
        dbc.Button("Download as SVG", color="primary", className="mr-1"),
        href=mirror_url,
        download="mirror.svg",
    )
    download_div = dbc.Row(
        [
            dbc.Col(
                [
                    html.Img(
                        src=(
                            f"/qrcode?mirror=true&usi1={quote(usi1)}&"
                            f"usi2={quote(usi2)}"
                        )
                    )
                ],
                className="col-1",
            ),
            dbc.Col(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                "Universal Spectrum Identifier 1",
                                className="col-4 font-weight-bold text-right",
                            ),
                            dbc.Col(
                                [
                                    usi1,
                                    " ",
                                    html.A(
                                        dbc.Badge(
                                            "Source",
                                            color="info",
                                            className="mr-1",
                                        ),
                                        href=source_link1,
                                    ),
                                ],
                                className="col-8",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                "SPLASH Identifier 1",
                                className="col-4 font-weight-bold text-right",
                            ),
                            dbc.Col(splash_key1, className="col-8"),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                "Universal Spectrum Identifier 2",
                                className="col-4 font-weight-bold text-right",
                            ),
                            dbc.Col(
                                [
                                    usi2,
                                    " ",
                                    html.A(
                                        dbc.Badge(
                                            "Source",
                                            color="info",
                                            className="mr-1",
                                        ),
                                        href=source_link2,
                                    ),
                                ],
                                className="col-8",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                "SPLASH Identifier 2",
                                className="col-4 font-weight-bold text-right",
                            ),
                            dbc.Col(splash_key2, className="col-8"),
                        ]
                    ),
                    dbc.Row(
                        [json_button, png_button, svg_button],
                        className="offset-2",
                    ),
                ],
                className="col-11",
            ),
        ]
    )

    return (download_div, image_obj, html.Br()), plotting_args


@dash_app.callback(
    [
        Output("output", "children"),
        Output("url", "search"),
        Output("debug", "children"),
    ],
    [
        Input("usi1", "value"),
        Input("usi2", "value"),
        Input("width", "value"),
        Input("height", "value"),
        Input("mz_min", "value"),
        Input("mz_max", "value"),
        Input("max_intensity", "value"),
        Input("annotate_precision", "value"),
        Input("annotation_rotation", "value"),
        Input("cosine", "value"),
        Input("fragment_mz_tolerance", "value"),
        Input("grid", "value"),
        Input("peak_table1", "derived_virtual_data"),
        Input("peak_table1", "derived_virtual_selected_rows"),
        Input("peak_table2", "derived_virtual_data"),
        Input("peak_table2", "derived_virtual_selected_rows"),
    ],
    [],
)
def draw_figure(
    usi1: str,
    usi2: str,
    width: float,
    height: float,
    mz_min: float,
    mz_max: float,
    max_intensity: float,
    annotate_precision: int,
    annotation_rotation: float,
    cosine: str,
    fragment_mz_tolerance: float,
    grid: bool,
    derived_virtual_data: List[Dict[str, str]],
    derived_virtual_selected_rows: List[int],
    derived_virtual_data2: List[Dict[str, str]],
    derived_virtual_selected_rows2: List[int],
) -> Tuple[Tuple[Any, Dict[str, Any]], str, str]:
    """
    Draw the figure for the given USI(s).

    Parameters
    ----------
    usi1 : str
        The first USI.
    usi2 : str
        The second USI (optional for a mirror plot).
    width : float
        The figure width.
    height : float
        The figure height.
    mz_min : float
        The minimum m/z value.
    mz_max : float
        The maximum m/z value.
    max_intensity : float
        The maximum intensity.
    annotate_precision : float
        The number of decimals to use for peak annotations.
    annotation_rotation : float
        The angle of the peak annotations.
    cosine : str
        The type of cosine similarity to compute.
    fragment_mz_tolerance : float
        The fragment m/z tolerance.
    grid : bool
        Whether or not to use a grid.
    derived_virtual_data : List[Dict[str, str]]
        The peaks of the first spectrum.
    derived_virtual_selected_rows : List[int]
        Indexes of the selected peaks in the first spectrum.
    derived_virtual_data2 : List[Dict[str, str]]
        The peaks of the second spectrum.
    derived_virtual_selected_rows2 : List[int]
        Indexes of the selected peaks in the second spectrum.

    Returns
    -------
    Tuple[Tuple[Any, Dict[str, Any]], str, str]
        A tuple with the HTML resources, the figure's URL parameters, and an
        empty string.
    """
    plotting_args = {
        "width": width,
        "height": height,
        "cosine": cosine,
        "grid": grid,
    }

    try:
        plotting_args["mz_min"] = float(mz_min)
    except (ValueError, TypeError):
        pass
    try:
        plotting_args["mz_max"] = float(mz_max)
    except (ValueError, TypeError):
        pass
    try:
        plotting_args["max_intensity"] = float(max_intensity)
    except (ValueError, TypeError):
        pass
    try:
        plotting_args["annotate_precision"] = int(annotate_precision)
    except (ValueError, TypeError):
        pass
    try:
        plotting_args["annotation_rotation"] = float(annotation_rotation)
    except (ValueError, TypeError):
        pass
    try:
        plotting_args["fragment_mz_tolerance"] = float(fragment_mz_tolerance)
    except (ValueError, TypeError):
        pass

    if usi1 and usi2:
        # Mirror spectra.
        plotting_args["usi1"], plotting_args["usi2"] = usi1, usi2

        annotation_masses, annotation_masses2 = [], []
        if derived_virtual_selected_rows is not None:
            annotation_masses = [
                derived_virtual_data[i]["m/z"]
                for i in derived_virtual_selected_rows
            ]
        if derived_virtual_selected_rows2 is not None:
            annotation_masses2 = [
                derived_virtual_data2[i]["m/z"]
                for i in derived_virtual_selected_rows2
            ]

        plotting_args["annotate_peaks"] = json.dumps(
            [annotation_masses, annotation_masses2]
        )
        spectrum_visualization, plotting_args = _process_mirror_usi(
            usi1, usi2, plotting_args
        )
    else:
        # Single spectrum.
        plotting_args["usi"] = plotting_args["usi1"] = usi1

        annotation_masses = []
        if derived_virtual_selected_rows is not None:
            annotation_masses = [
                derived_virtual_data[i]["m/z"]
                for i in derived_virtual_selected_rows
            ]

        plotting_args["annotate_peaks"] = json.dumps([annotation_masses])
        spectrum_visualization, plotting_args = _process_single_usi(
            usi1, plotting_args
        )

    return (
        spectrum_visualization,
        f"?{urlencode(plotting_args, quote_via=quote)}",
        "",
    )


@dash_app.callback(
    [
        Output("peak_table1", "data"),
        Output("peak_table1", "columns"),
        Output("peak_table1", "selected_rows"),
        Output("peak_table2", "data"),
        Output("peak_table2", "columns"),
        Output("peak_table2", "selected_rows"),
    ],
    [Input("usi1", "value"), Input("usi2", "value"), Input("url", "pathname")],
    [State("url", "search")],
)
def draw_table(usi1: str, usi2: str, pathname: str, search: str) -> Tuple[List[Dict[str, float]], List[Dict[str, str]], List[int],
                                                                          List[Dict[str, float]], List[Dict[str, str]], List[int]]:
    """
    Plot the table for the given USI(s).

    Parameters
    ----------
    usi1 : str
        The first USI.
    usi2 : str
        The second USI (optional).
    pathname : str
        URL path.
    search : str
        URL-encoded parameter string.

    Returns
    -------
    Tuple[List[Dict[str, float]], List[Dict[str, str]], List[int],
          List[Dict[str, float]], List[Dict[str, str]], List[int]]
        For both spectra: (i) The spectrum's peaks as a dictionary of "m/z" and
        "Intensity" values; (ii) a dictionary of the column labels; (iii) a
        list with peak indexes.
    """
    plotting_args = {}

    # Determine URL override.
    triggered_ids = [p["prop_id"] for p in dash.callback_context.triggered]
    if "url.pathname" in triggered_ids:
        # Doing override from URL for selected rows.
        query_dict = parse_qs(search[1:])

        annotate_peaks = _get_url_param(query_dict, "annotate_peaks", None)
        if annotate_peaks is not None:
            plotting_args["annotate_peaks"] = annotate_peaks
            plotting_args["fragment_mz_tolerance"] = float(
                _get_url_param(
                    query_dict,
                    "fragment_mz_tolerance",
                    defaults["fragment_mz_tolerance"],
                )
            )

    # Set up parameters from URL.
    peaks1, columns1, selected_rows1 = _process_single_usi_table(
        usi1, plotting_args
    )
    if usi2:
        peaks2, columns2, selected_rows2 = _process_single_usi_table(
            usi2, plotting_args
        )
    else:
        peaks2, columns2, selected_rows2 = [], dash.no_update, []

    return peaks1, columns1, selected_rows1, peaks2, columns2, selected_rows2


@dash_app.callback(
    [
        Output("left_panel_col", "className"),
        Output("right_panel_col", "className"),
    ],
    [Input("ui_width", "value"),],
    [],
)
def set_ui_width(ui_width: int) -> Tuple[str, str]:
    """
    Modify the size of the settings panel.

    Parameters
    ----------
    ui_width : int
        The scale of the settings panel.

    Returns
    -------
    Tuple[str, str]
        String encodings of the column width for the UI panel and the
        neighboring panel.
    """
    return f"col-{ui_width}", f"col-{12 - ui_width}"


@dash_app.callback(
    [Output("reset_figure", "href")],
    [Input("usi1", "value"), Input("usi2", "value")],
    [],
)
def create_reset(usi1: str, usi2: str) -> List[str]:
    """
    Reset the drawing parameters of the spectrum plot.

    Parameters
    ----------
    usi1 : str
        The first USI.
    usi2 : str
        The second USI (optional).

    Returns
    -------
    List[str]
        The USI URL without drawing parameters.
    """
    if usi1 and usi2:
        return [f"/dashinterface/?usi1={quote(usi1)}&usi2={quote(usi2)}"]
    else:
        return [f"/dashinterface/?usi={quote(usi1)}"]


if __name__ == "__main__":
    dash_app.run_server(host="0.0.0.0", port=5000, debug=True)
