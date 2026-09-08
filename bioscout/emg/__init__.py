"""EMG domain code: filtering, channel mapping, MVC normalisation, analysis.

A domain package, not a CLI verb -- ``session/`` (export, channel resolution)
and ``simulate/ceinms/`` (excitation QC) both import from here, the same way
everything already imports ``core/``.

    filter.py     filter-SETTINGS resolution (session.yaml -> BatchSettings
                  -> defaults), not signal processing
    normalise.py  rectify / envelope / session-max MVC normalisation
    channels.py   channel-name -> muscle resolution
    analysis.py   NMF synergies, CEINMS-readiness frequency QC
    emg.py        the shared EMG data helpers

Nothing is imported eagerly (scipy/pandas stay unloaded until used).
"""

# bioscout.utils is imported first, for the same ordering reason as
# bioscout/core/__init__.py and bioscout/session/__init__.py: emg.py binds
# bioscout.utils at module level and bioscout/utils/__init__.py re-exports
# filter_emg and friends FROM emg.py, so the cycle only unties if utils starts.
# While these files lived in utils/ the parent-package rule guaranteed it.
import bioscout.utils as _utils_first   # noqa: F401  (import for ordering)
