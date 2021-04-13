import gc
import io

from typing import Any, Dict, List, Optional, Tuple

from spectrum_utils import plot as sup, spectrum as sus
import matplotlib.pyplot as plt

from config import USI_SERVER


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
