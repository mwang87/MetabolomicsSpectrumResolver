import gc
import io
from typing import Any

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from spectrum_utils import plot as sup, spectrum as sus

from config import USI_SERVER
import similarity


matplotlib.use('Agg')


def generate_figure(spectrum: sus.MsmsSpectrum, extension: str,
                    **kwargs: Any) -> io.BytesIO:
    """
    Generate a spectrum plot.

    Parameters
    ----------
    spectrum : sus.MsmsSpectrum
        The spectrum to be plotted.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the spectrum plot.
    """
    usi = spectrum.identifier

    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    sup.spectrum(
        spectrum, annotate_ions=kwargs['annotate_peaks'],
        annot_kws={'rotation': kwargs['annotation_rotation'], 'clip_on': True},
        grid=kwargs['grid'], ax=ax)

    ax.set_xlim(kwargs['mz_min'], kwargs['mz_max'])
    ax.set_ylim(0, kwargs['max_intensity'])

    if not kwargs['grid']:
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

    title = ax.text(0.5, 1.06, kwargs['plot_title'],
                    horizontalalignment='center', verticalalignment='bottom',
                    fontsize='x-large', fontweight='bold',
                    transform=ax.transAxes)
    title.set_url(f'{USI_SERVER}spectrum/?usi={usi}')
    subtitle = (f'Precursor $m$/$z$: '
                f'{spectrum.precursor_mz:.{kwargs["annotate_precision"]}f} '
                if spectrum.precursor_mz > 0 else '')
    subtitle += f'Charge: {spectrum.precursor_charge}'
    subtitle = ax.text(0.5, 1.02, subtitle, horizontalalignment='center',
                       verticalalignment='bottom', fontsize='large',
                       transform=ax.transAxes)
    subtitle.set_url(f'{USI_SERVER}spectrum/?usi={usi}')

    buf = io.BytesIO()
    plt.savefig(buf, bbox_inches='tight', format=extension)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    gc.collect()

    return buf


def generate_mirror_figure(spectrum_top: sus.MsmsSpectrum,
                           spectrum_bottom: sus.MsmsSpectrum,
                           extension: str, **kwargs: Any) -> io.BytesIO:
    """
    Generate a mirror plot of two spectra.

    Parameters
    ----------
    spectrum_top : sus.MsmsSpectrum
        The spectrum to be plotted at the top of the mirror plot.
    spectrum_bottom : sus.MsmsSpectrum
        The spectrum to be plotted at the bottom of the mirror plot.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the mirror plot.
    """
    usi1 = spectrum_top.identifier
    usi2 = spectrum_bottom.identifier

    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    # Determine cosine similarity and matching peaks.
    if kwargs['cosine']:
        # Assign the matching peak annotations.
        sim_score, peak_matches = similarity.cosine(
            spectrum_top, spectrum_bottom, kwargs['fragment_mz_tolerance'],
            kwargs['cosine'] == 'shifted')
        peak_matches = zip(*peak_matches)
    else:
        sim_score = 0
        # Make sure that top and bottom spectra are colored..
        peak_matches = [np.arange(len(spectrum_top.annotation)),
                        np.arange(len(spectrum_bottom.annotation))]

    if spectrum_top.peptide is None:
        # Initialize the annotations as unmatched.
        for annotation in spectrum_top.annotation:
            if annotation is not None:
                annotation.ion_type = 'unmatched'
        for annotation in spectrum_bottom.annotation:
            if annotation is not None:
                annotation.ion_type = 'unmatched'

        for peak_idx, spectrum, label in zip(peak_matches,
                                             [spectrum_top, spectrum_bottom],
                                             ['top', 'bottom']):
            for i in peak_idx:
                if spectrum.annotation[i] is None:
                    spectrum.annotation[i] = sus.FragmentAnnotation(
                        0, spectrum.mz[i], '')
                spectrum.annotation[i].ion_type = label

        # Colors for mirror plot peaks (subject to change).
        sup.colors['top'] = '#212121'
        sup.colors['bottom'] = '#388E3C'
        sup.colors['unmatched'] = 'darkgray'
        sup.colors[None] = 'darkgray'

        sup.mirror(spectrum_top, spectrum_bottom,
                   {'annotate_ions': kwargs['annotate_peaks'],
                    'annot_kws': {'rotation': kwargs['annotation_rotation'],
                                  'clip_on': True},
                    'grid': kwargs['grid']}, ax=ax)
    else:
        sup.mirror(spectrum_top, spectrum_bottom,
                   {'annot_kws': {'rotation': kwargs['annotation_rotation'],
                                  'clip_on': True},
                    'grid': kwargs['grid']}, ax=ax)

    ax.set_xlim(kwargs['mz_min'], kwargs['mz_max'])
    ax.set_ylim(-kwargs['max_intensity'], kwargs['max_intensity'])

    if not kwargs['grid']:
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

    text_y = 1.2 if kwargs['cosine'] else 1.15
    for usi, spec, loc in zip([usi1, usi2], [spectrum_top, spectrum_bottom],
                              ['Top', 'Bottom']):
        title = ax.text(0.5, text_y, f'{loc}: {usi}',
                        horizontalalignment='center',
                        verticalalignment='bottom',
                        fontsize='x-large',
                        fontweight='bold',
                        transform=ax.transAxes)
        title.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
        text_y -= 0.04
        subtitle = (
            f'Precursor $m$/$z$: '
            f'{spec.precursor_mz:.{kwargs["annotate_precision"]}f} '
            if spec.precursor_mz > 0 else '')
        subtitle += f'Charge: {spec.precursor_charge}'
        subtitle = ax.text(0.5, text_y, subtitle, horizontalalignment='center',
                           verticalalignment='bottom', fontsize='large',
                           transform=ax.transAxes)
        subtitle.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
        text_y -= 0.06

    if kwargs['cosine']:
        subtitle_score = f'Cosine similarity = {sim_score:.4f}'
        ax.text(0.5, text_y, subtitle_score, horizontalalignment='center',
                verticalalignment='bottom', fontsize='x-large',
                fontweight='bold', transform=ax.transAxes)

    buf = io.BytesIO()
    plt.savefig(buf, bbox_inches='tight', format=extension)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    gc.collect()

    return buf
