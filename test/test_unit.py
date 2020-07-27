from metabolomics_spectrum_resolver.usi_test_cases import test_usi_list

from metabolomics_spectrum_resolver import parsing, views


def test_uri_parse():
    for usi in test_usi_list:
        print(f'TESTING USI {usi}')
        parsing.parse_usi(usi)


def test_render_mirror():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'] = 0
    plotting_params['mz_max'] = 250
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    views._generate_mirror_figure(
        'mzspec:MASSBANK::accession:BSU00002',
        'mzspec:MASSBANK::accession:BSU00002',
        'png', **plotting_params)


def test_render_single_plot():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'] = 0
    plotting_params['mz_max'] = 250
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    views._generate_figure(
        'mzspec:MASSBANK::accession:BSU00002', 'png', **plotting_params)


def test_render_single_plot_annotated():
    plotting_params = views.default_plotting_args
    plotting_params['mz_min'] = 100
    plotting_params['mz_max'] = 200
    plotting_params['annotate_peaks'] = (
        [75.0225, 93.0575, 128.0275, 139.0075], [])
    plotting_params['max_intensity'] = plotting_params['max_intensity_labeled']
    views._generate_figure(
        'mzspec:MS2LDA:TASK-190:accession:270684', 'png', **plotting_params)
