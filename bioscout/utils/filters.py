"""Generic zero-phase signal filtering -- the primitives, with no domain in them.

Pulled out of ``emg_normalise.filter_emg()``'s inline ``scipy.signal``
butter+filtfilt calls (docs/RESTRUCTURE_PLAN.md, stage 11). Nothing here knows
what EMG is: ``bioscout.emg.normalise`` supplies the cutoffs and the column
loop, this supplies the filter. Other inline filtering in the codebase
(``simulate/gapfill.py`` is the next candidate) migrates in over time rather
than in one audit.

``filtfilt`` is used rather than ``lfilter`` on purpose: it filters forwards
and backwards, so the result has no phase lag. That matters for anything whose
TIMING is read afterwards -- an EMG envelope lined up against a gait event, a
force trace lined up against a marker trajectory. The cost is that the
effective filter order is doubled, which is why the orders here look low.

    from bioscout.utils.filters import bandpass, lowpass

    env = lowpass(np.abs(bandpass(raw, fs=2000, lowcut=20, highcut=95)),
                  fs=2000, cutoff=6)
"""
from __future__ import annotations

__all__ = ["bandpass", "lowpass", "nyquist_fraction"]


def nyquist_fraction(freq, fs):
    """``freq`` as a fraction of the Nyquist rate -- what ``butter`` wants.

    Returns >= 1.0 when the cutoff is at or above Nyquist, which is the caller's
    cue that the request is not filterable at this sampling rate.
    """
    return float(freq) / (0.5 * float(fs))


def bandpass(x, fs, lowcut, highcut, order=4):
    """Zero-phase Butterworth band-pass of a 1-D signal.

    Args:
        x: the samples (anything ``filtfilt`` accepts -- list, ndarray, Series).
        fs: sampling rate in Hz.
        lowcut, highcut: passband edges in Hz.
        order: Butterworth order BEFORE the forward-backward pass doubles it.

    Raises ValueError when the band is not realisable at this sampling rate
    (edges crossed, or at/above Nyquist) rather than returning a silently
    wrong signal -- scipy would otherwise raise a less specific error, or
    design a filter that does not do what was asked.
    """
    from scipy.signal import butter, filtfilt

    low = nyquist_fraction(lowcut, fs)
    high = nyquist_fraction(highcut, fs)
    if low >= high:
        raise ValueError(
            f"band-pass low cutoff ({lowcut} Hz) is at or above the high cutoff "
            f"({highcut} Hz) at fs={fs} Hz")
    if high >= 1.0:
        raise ValueError(
            f"band-pass high cutoff ({highcut} Hz) is at or above Nyquist "
            f"({0.5 * fs} Hz) at fs={fs} Hz")
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, x)


def lowpass(x, fs, cutoff, order=4):
    """Zero-phase Butterworth low-pass of a 1-D signal.

    Same contract as :func:`bandpass`; raises ValueError when ``cutoff`` is at
    or above Nyquist.
    """
    from scipy.signal import butter, filtfilt

    low = nyquist_fraction(cutoff, fs)
    if low >= 1.0:
        raise ValueError(
            f"low-pass cutoff ({cutoff} Hz) is at or above Nyquist "
            f"({0.5 * fs} Hz) at fs={fs} Hz")
    b, a = butter(order, low, btype="low")
    return filtfilt(b, a, x)
