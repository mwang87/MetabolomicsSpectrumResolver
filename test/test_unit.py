import sys
sys.path.insert(0, "..")
import parsing  # noqa: E402

import views
from usi_test_cases import test_usi_list


def test_uri_parse():
    for usi in test_usi_list:
        parsing.parse_usi(usi)


def test_render_mirror():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'] = 0
    plotting_params['mz_max'] = 250
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    views._generate_mirror_figure(
        'mzdata:MASSBANK:BSU00002', 'mzdata:MASSBANK:BSU00002', 'png',
        **plotting_params)


def test_render_single_plot():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'] = 0
    plotting_params['mz_max'] = 250
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    views._generate_figure(
        'mzdata:MASSBANK:BSU00002', 'png',
        **plotting_params)


def test_render_single_plot_annotated():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'] = 100
    plotting_params['mz_max'] = 200
    plotting_params['annotate_peaks'] = (
        [75.0225, 93.0575, 128.0275, 139.0075], [])
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    views._generate_figure(
        'mzspec:MS2LDATASK-190:document:270684', 'png',
        **plotting_params)
