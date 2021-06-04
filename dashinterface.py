from urllib.parse import urlencode, quote, parse_qs
from typing import Any, Dict, List, Tuple

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import requests
from dash.dependencies import Input, Output, State

import tasks
import views
from app import app


_example_usi = "mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077"

dash_app = dash.Dash(
    name="dashinterface",
    server=app,
    url_base_pathname="/dashinterface/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
dash_app.title = "USI"

dash_app.index_string = """<!DOCTYPE html>
<html>
    <head>
        <!-- Global site tag (gtag.js) - Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=UA-8412213-8"></script>
        <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());

        gtag('config', 'UA-8412213-8');
        </script>
        
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

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
                    dbc.NavLink("Metabolomics USI — Dash Interface", href="#"),
                ),
                dbc.NavItem(
                    html.A("Homepage", href="/", className="nav-link")
                ),
            ],
            navbar=True,
        ),
    ],
    color="light",
    dark=False,
    sticky="top",
)

DATASELECTION_CARD = [
    dbc.CardHeader(dbc.Row([
            dbc.Col(
                html.H5("USI Data Selection")
            ),
            dbc.Col(
                html.A(
                    dbc.Button("Link to Plot", 
                        color="primary", size="sm", 
                        className="mr-1", 
                        style={
                            "float" : "right"
                        }
                    ),
                    id="plot_link", 
                )
            )
    ])),
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
                                    {"label": "Yes", "value": "True"},
                                    {"label": "No", "value": "False"},
                                ],
                                value="True",
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
                "Wout Bittremieux, Christopher Chen, Pieter C. Dorrestein, "
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
            html.Br(),
            html.A(
                "Mirror Plot",
                href=(
                    "/dashinterface/?usi1=mzspec%3AGNPS%3ATASK-8925aa40e48e468ca9ba02955ee369e6-spectra%2Fspecs_ms.mgf%3Ascan%3A1618&usi2=mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00000072217&width=10.0&height=6.0&mz_min=None&mz_max=None&max_intensity=150&annotate_precision=4&annotation_rotation=90&cosine=standard&fragment_mz_tolerance=1.0&grid=True&annotate_peaks=%5B%5B527.1060180664062%2C%20689.155029296875%2C%20791.1669921875%2C%20833.1929931640625%5D%2C%20%5B527.3635864257812%2C%20689.3635864257812%2C%20791.45458984375%2C%20833.3635864257812%5D%5D"
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
def set_drawing_controls(
    _: str, search: str
) -> Tuple[
    str, str, str, str, str, str, str, str, str, str, str, str,
]:
    """
    Set the drawing controls from the URL query parameters.

    Parameters
    ----------
    _ : str
        The URL path string. This is not used but needed to trigger the
        callback.
    search : str
        The URL query string.

    Returns
    -------
    Tuple[str, str, str, str, str, str, str, str, str, str, str, str,]
        The drawing controls (as strings or `dash.no_update` if no interface
        update should be triggered):
        - The first USI.
        - The second USI.
        - The figure width.
        - The figure height.
        - The minimum m/z value.
        - The maximum m/z value.
        - The maximum intensity value.
        - The m/z precision of peak labels.
        - The angle of peak labels.
        - The type of cosine score.
        - The fragment m/z tolerance.
        - Whether to display the grid.
    """
    drawing_controls = parse_qs(search[1:])
    return (
        drawing_controls.get("usi1", drawing_controls.get("usi", [_example_usi]))[0],
        drawing_controls.get("usi2", [dash.no_update])[0],
        drawing_controls.get("width", [dash.no_update])[0],
        drawing_controls.get("height", [dash.no_update])[0],
        drawing_controls.get("mz_min", [dash.no_update])[0],
        drawing_controls.get("mz_max", [dash.no_update])[0],
        drawing_controls.get("max_intensity", [dash.no_update])[0],
        drawing_controls.get("annotate_precision", [dash.no_update])[0],
        drawing_controls.get("annotation_rotation", [dash.no_update])[0],
        drawing_controls.get("cosine", [dash.no_update])[0],
        drawing_controls.get("fragment_mz_tolerance", [dash.no_update])[0],
        drawing_controls.get("grid", [dash.no_update])[0],
    )


@dash_app.callback(
    [Output("output", "children"), Output("url", "search"), Output("plot_link", "href")],
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
)
def draw_figure(
    usi1: str,
    usi2: str,
    width: float,
    height: float,
    mz_min: float,
    mz_max: float,
    max_intensity: int,
    annotate_precision: int,
    annotation_rotation: int,
    cosine: str,
    fragment_mz_tolerance: float,
    grid: bool,
    peak_table1: List[Dict[str, str]],
    peak_table1_selected_rows: List[int],
    peak_table2: List[Dict[str, str]],
    peak_table2_selected_rows: List[int],
) -> Tuple[Tuple[Any, Dict[str, Any]], str]:
    """
    Draw the figure for the given USI(s).

    Parameters
    ----------
    usi1 : str
        The first USI input.
    usi2 : str
        The second USI input (optional; if specified a mirror plot will be
        drawn).
    width : float
        The figure width.
    height : float
        The figure height.
    mz_min : float
        The minimum m/z value.
    mz_max : float
        The maximum m/z value.
    max_intensity : float
        The maximum intensity value.
    annotate_precision : int
        The m/z precision of peak labels.
    annotation_rotation : int
        The angle of peak labels.
    cosine : str
        The type of cosine score.
    fragment_mz_tolerance : float
        The fragment m/z tolerance.
    grid : bool
        Whether to display the grid.
    peak_table1 : List[Dict[str, str]]
        The table of peaks (m/z and intensity values) for the first spectrum.
    peak_table1_selected_rows : List[int]
        Indexes of the selected peaks for the first spectrum.
    peak_table2 : List[Dict[str, str]]
        The table of peaks (m/z and intensity values) for the second spectrum.
    peak_table2_selected_rows : List[int]
        Indexes of the selected peaks for the second spectrum.

    Returns
    -------
    Tuple[Tuple[Any, Dict[str, Any]], str]
        A tuple with the plot's (i) HTML resources, (ii) URL query string.
    """

    annotated_peaks = [
            [float(peak_table1[i]["m/z"]) for i in peak_table1_selected_rows],
            [float(peak_table2[i]["m/z"]) for i in peak_table2_selected_rows],
        ]

    drawing_controls = views.get_drawing_controls(
        usi1=usi1,
        usi2=usi2,
        width=width,
        height=height,
        mz_min=mz_min,
        mz_max=mz_max,
        max_intensity=max_intensity,
        annotate_precision=annotate_precision,
        annotation_rotation=annotation_rotation,
        cosine=cosine,
        fragment_mz_tolerance=fragment_mz_tolerance,
        grid=grid,
        annotate_peaks=[
            [float(peak_table1[i]["m/z"]) for i in peak_table1_selected_rows],
            [float(peak_table2[i]["m/z"]) for i in peak_table2_selected_rows],
        ],
    )

    # Single spectrum plot or mirror spectrum plot.
    if not usi2:
        del drawing_controls["usi2"]
        spectrum_view = _process_usi(usi1, drawing_controls)
    else:
        spectrum_view = _process_mirror_usi(usi1, usi2, drawing_controls)

    return [spectrum_view, f"?{urlencode(drawing_controls, quote_via=quote)}", f"/dashinterface?{urlencode(drawing_controls, quote_via=quote)}"]


def _process_usi(
    usi: str, drawing_controls: Dict[str, Any]
) -> Tuple[Any, Any]:
    """
    Process the given USI for plotting.

    Parameters
    ----------
    usi : str
        The USI to process.
    drawing_controls : Dict[str, Any]
        The drawing controls to plot the spectrum.

    Returns
    -------
    Tuple[Any, Any]
        A tuple with the HTML elements to show the spectrum plot: (i) the div
        in which the spectrum plot is shown, and (ii) the HTML img for the
        spectrum plot.
    """
    _, source_link, splash_key = tasks.parse_usi(usi)

    usi_url = f"/svg/?{urlencode(drawing_controls, quote_via=quote)}"
    # Pre-fetch the spectrum plot to warm the cache.
    requests.get(f"http://localhost:5000{usi_url}")

    image_obj = html.Img(src=usi_url)

    json_button = html.A(
        dbc.Button("Download as JSON", color="primary", className="mr-1"),
        href=f"/json/?usi1={quote(usi)}",
    )
    csv_button = html.A(
        dbc.Button("Download as CSV", color="primary", className="mr-1"),
        href=f"/csv/?usi1={quote(usi)}",
    )
    png_button = html.A(
        dbc.Button("Download as PNG", color="primary", className="mr-1"),
        href=f"/png/?{urlencode(drawing_controls, quote_via=quote)}",
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

    return download_div, image_obj


def _process_mirror_usi(
    usi1: str, usi2: str, drawing_controls: Dict[str, Any]
) -> Tuple[Any, Any, Any]:
    """
    Process the given USIs for plotting in a mirror plot.

    Parameters
    ----------
    usi1 : str
        The first USI to process.
    usi2 : str
        The second USI to process.
    drawing_controls : Dict[str, Any]
        The drawing controls to create the mirror plot.

    Returns
    -------
    Tuple[Any, Any, Any]
        A tuple with the HTML elements to show the spectrum plot: (i) the div
        in which the spectrum plot is shown, (ii) the HTML img for the mirror
        plot, and (iii) a line break.
    """
    _, source_link1, splash_key1 = tasks.parse_usi(usi1)
    _, source_link2, splash_key2 = tasks.parse_usi(usi2)

    mirror_url = f"/svg/mirror/?{urlencode(drawing_controls, quote_via=quote)}"
    # Pre-fetch the mirror plot to warm the cache.
    requests.get(f"http://localhost:5000{mirror_url}")

    image_obj = html.Img(src=mirror_url)

    json_button = html.A(
        dbc.Button("Download as JSON", color="primary", className="mr-1"),
        href=f"/json/mirror?{urlencode(drawing_controls, quote_via=quote)}",
    )
    png_button = html.A(
        dbc.Button("Download as PNG", color="primary", className="mr-1"),
        href=f"/png/mirror?{urlencode(drawing_controls, quote_via=quote)}",
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

    return download_div, image_obj, html.Br()


@dash_app.callback(
    [
        Output("peak_table1", "columns"),
        Output("peak_table1", "data"),
        Output("peak_table1", "selected_rows"),
        Output("peak_table2", "columns"),
        Output("peak_table2", "data"),
        Output("peak_table2", "selected_rows"),
    ],
    [
        Input("usi1", "value"),
        Input("usi2", "value"),
        Input("mz_min", "value"),
        Input("mz_max", "value"),
        Input("annotate_precision", "value"),
    ],
    [State("url", "search")]
)
def draw_table(
    usi1: str, usi2: str, mz_min: str, mz_max: str, annotate_precision: str, search: str
) -> Tuple[
    List[Dict[str, str]],
    List[Dict[str, float]],
    List[int],
    List[Dict[str, str]],
    List[Dict[str, float]],
    List[int],
]:
    """
    Show the table for the given USI(s).

    Parameters
    ----------
    usi1 : str
        The first USI.
    usi2 : str
        The second USI (optional).
    mz_min : float
        The minimum m/z value.
    mz_max : float
        The maximum m/z value.
    annotate_precision : float
        The m/z precision of peak labels.

    Returns
    -------
    Tuple[List[Dict[str, str]], List[Dict[str, float]], List[int],
         List[Dict[str, str]], List[Dict[str, float]], List[int]]
        A tuple with table data for both spectra: (i) a dictionary of the
        column labels, (ii) the spectrum's peaks as a dictionary of "m/z" and
        "Intensity" values, (iii) a list of indexes of the selected peaks.
        If only a single USI is being processed, data for the second table is
        empty.
    """

    annotate_peaks1 = True
    annotate_peaks2 = True
    try:
        import json
        url_params = parse_qs(search[1:])
        annotate_peaks = json.loads(url_params["annotate_peaks"][0])
        annotate_peaks1 = annotate_peaks[0]
        annotate_peaks2 = annotate_peaks[1]
    except KeyError:
        pass

    mz_min = None if mz_min == "None" else mz_min
    mz_max = None if mz_max == "None" else mz_max

    columns1 = columns2 = [
        {"name": "m/z", "id": "m/z"},
        {"name": "Intensity", "id": "Intensity"},
    ]
    peak_controls = {
        "mz_min": float(mz_min) if mz_min is not None else None,
        "mz_max": float(mz_max) if mz_max is not None else None,
        "fragment_mz_tolerance": 0.001,
        "annotate_precision": int(annotate_precision),
        "annotate_peaks": annotate_peaks1,
    }

    peaks1, peaks1_selected_i = _get_peaks(usi1, peak_controls)
    if usi2:
        peak_controls["annotate_peaks"] = annotate_peaks2
        peaks2, peaks2_selected_i = _get_peaks(usi2, peak_controls)
    else:
        peaks2, peaks2_selected_i, columns2 = [], [], dash.no_update

    return (
        columns1,
        peaks1,
        peaks1_selected_i,
        columns2,
        peaks2,
        peaks2_selected_i,
    )


def _get_peaks(
    usi: str, peak_controls: Dict[str, Any]
) -> Tuple[List[Dict[str, float]], List[int]]:
    """
    Generate a peak table for the given USI.

    Parameters
    ----------
    usi : str
        The USI for which to generate a peak table.
    peak_controls : Dict[str, Any]
        A dictionary with settings to filter the spectrum's peaks.

    Returns
    -------
    Tuple[List[Dict[str, float]], List[int]]
        A tuple with (i) the spectrum's peaks as a dictionary of "m/z" and
        "Intensity" values; (ii) a list with indexes of the selected peaks.
    """
    # noinspection PyTypeChecker
    spectrum = views.prepare_spectrum(tasks.parse_usi(usi)[0], **peak_controls)
    peaks = [
        {
            "m/z": round(mz, peak_controls["annotate_precision"]),
            "Intensity": round(intensity * 100, 1),
        }
        for mz, intensity in zip(spectrum.mz, spectrum.intensity)
    ]
    selected_peaks = spectrum.annotation.nonzero()[0].tolist()
    return peaks, selected_peaks


@dash_app.callback(
    [
        Output("left_panel_col", "className"),
        Output("right_panel_col", "className"),
    ],
    [Input("ui_width", "value")],
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
