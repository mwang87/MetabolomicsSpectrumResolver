import sys
sys.path.insert(0, '..')

import parsing
import views

import usi_test_cases


def test_usi_parse():
    for usi in usi_test_cases.test_usi_list:
        parsing.parse_usi(usi)


def test_render_mirror():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'], plotting_params['mz_max'] = 0, 250
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    spectrum1, _ = parsing.parse_usi('mzspec:MASSBANK::accession:BSU00002')
    spectrum2, _ = parsing.parse_usi('mzspec:MASSBANK::accession:BSU00002')
    views._generate_mirror_figure(spectrum1, spectrum2, 'png',
                                  **plotting_params)


def test_render_single_plot():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'], plotting_params['mz_max'] = 0, 250
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    spectrum, _ = parsing.parse_usi('mzspec:MASSBANK::accession:BSU00002')
    views._generate_figure(spectrum, 'png', **plotting_params)


def test_render_single_plot_annotated():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'], plotting_params['mz_max'] = 0, 200
    plotting_params['annotate_peaks'] = (
        [75.0225, 93.0575, 128.0275, 139.0075], [])
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    spectrum, _ = parsing.parse_usi('mzspec:MS2LDA:TASK-190:accession:270684')
    views._generate_figure(spectrum, 'png', **plotting_params)
