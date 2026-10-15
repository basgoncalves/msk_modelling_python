"""Low-level OpenSim wrapper plumbing shared by ``model/`` and ``simulate/``.

Loading a model, reading its assembly accuracy, and silencing OpenSim's logger
are fundamentally about the MODEL, so they live here; ``bioscout.simulate``
imports from this module and nothing here imports back from it.

Split out of the old ``bioscout/utils/openSim.py`` (docs/RESTRUCTURE_PLAN.md,
stage 6) -- the code is unchanged, only its address.
"""
import os
import sys
import contextlib as _contextlib
import functools as _functools
import opensim as osim

try:                                    # the project's settings.py, if it has one
    from bioscout import settings
except Exception:                       # noqa: BLE001 - absent or mid-cycle
    settings = None


def _assembly_accuracy(default=1e-8):
    """Model assembly/constraint tolerance to use when loading models.

    Constraint-coupled knees (Lerner/JAM, GPK, patella couplers) frequently miss
    OpenSim's ultra-tight default constraint tolerance during assemble(), spamming
    'Unable to achieve required assembly error tolerance' before it relaxes and
    recovers. Loosening to ~1e-8 (physically negligible for joint moments / JCF)
    silences it. Override via BatchSettings.assembly_accuracy in a project."""
    try:
        from bioscout import utils as _u
        v = getattr(getattr(_u, "settings", None), "BatchSettings", None)
        v = getattr(v, "assembly_accuracy", None)
        return float(v) if v else default
    except Exception:
        return default

def _stdout_is_console():
    """True when fd 1 must NOT be swapped for devnull.

    On Windows ``sys.stdout`` wraps a _WindowsConsoleIO bound to the console
    HANDLE, not to fd 1; swapping fd 1 leaves it writing to a handle that is no
    longer a console and the next ordinary print() dies with
    "OSError: [WinError 1] Incorrect function". Under MINGW / Git Bash fd 1 is a
    pty and the same thing happens. Either way the redirect is unsafe."""
    import sys as _sys
    # bioscout's quiet CLI mode (every `simulate`/`session` verb without
    # --verbose) has already replaced sys.stdout with a tee into the log file
    # and a null console stream: no Python print() reaches the console handle,
    # so swapping fd 1 is safe -- and it is the ONLY thing that silences the
    # C++ printBasicInfo block on a Windows console, where the logger level is
    # not enough. Without this the block still reached the terminal six
    # times per exbiomec run, precisely in the mode meant to be quiet.
    try:
        from bioscout.utils import shared as _sh
        if getattr(_sh, "QUIET_CONSOLE", False):
            return False
    except Exception:                                        # noqa: BLE001
        pass
    try:
        _raw = getattr(getattr(_sys.stdout, "buffer", None), "raw", None)
        return (os.name == "nt"
                and (type(_raw).__name__ == "_WindowsConsoleIO"
                     or _sys.stdout.isatty()))
    except Exception:                                        # noqa: BLE001
        return os.name == "nt"

def _quiet_model(arg):
    """``osim.Model(arg)`` with its printBasicInfo() dump suppressed.

    Constructing a Model writes a fixed block to std::cout from C++::

                   MODEL: 021
             coordinates: 39
                  forces: 97
             ...
        misc modelcomponents: 0

    On OpenSim 4.3+ it goes through the logger (log_info), so Logger level
    "off" suppresses it -- but the tools reset the logger to 'info' as they run,
    so the level is re-applied here immediately before EVERY construction. It
    bypasses sys.stdout, so the _Tee log filter never sees it; where fd 1 can be
    swapped safely (not a console) we redirect too, as belt and braces.

    The redirect here is now gated on _stdout_is_console() -- it was unconditional,
    which corrupted Git Bash. It used to be deliberately not gated on
    opensim_log_level like _osim_quiet_ctx(). That gate reads `settings`, which
    openSim.py resolves via a sys.path insert of its own directory, so which
    module it lands on depends on how the process was started; the block kept
    leaking through as a result. printBasicInfo carries no diagnostic value, and
    fd 2 (stderr) stays open throughout, so genuine OpenSim errors still surface.
    """
    import sys as _sys
    # The primary mechanism: Model::printBasicInfo() goes through OpenSim's
    # logger (log_info) on 4.3+, so setting the level to "off" suppresses it
    # without touching any file descriptor. OpenSim's tools reset the logger to
    # 'info' as they run, so it must be re-applied here, immediately before the
    # construction, not once at import.
    _quiet_osim()
    try:
        _sys.stdout.flush()
    except Exception:
        pass
    if _stdout_is_console():
        # Never swap fd 1 out from under a console -- that is what left Git Bash
        # unusable. The logger level above is the whole suppression here.
        return osim.Model(arg)
    try:
        _saved = os.dup(1)
    except Exception:                     # no real fd 1 (embedded/captured stdout)
        return osim.Model(arg)
    _devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(_devnull, 1)
        return osim.Model(arg)
    finally:
        try:
            os.dup2(_saved, 1)
        finally:
            os.close(_devnull)
            os.close(_saved)

def load_model(path, accuracy=None):
    """opensim.Model(path) with a relaxed assembly accuracy applied (see
    _assembly_accuracy). Use everywhere a model is loaded for a tool run."""
    model = _quiet_model(path)
    acc = accuracy if accuracy is not None else _assembly_accuracy()
    try:
        model.set_assembly_accuracy(acc)
    except Exception:
        pass
    return model

def _quiet_osim():
    """Apply the configured OpenSim log level (settings.BatchSettings.
    opensim_log_level, e.g. "off"/"error"). Uses the Level_* ENUM — proven to work
    on the installed build — and reads the flag from the LOADED project settings
    (bioscout.utils.settings) first, falling back to this module's ``settings``.
    OpenSim's tools reset the logger to 'info' when they run, so this is re-applied
    before each tool via the ``_quiet_console`` decorator."""
    try:
        _lvl = None
        try:
            from bioscout import utils as _u
            _bs = getattr(getattr(_u, "settings", None), "BatchSettings", None)
            _lvl = getattr(_bs, "opensim_log_level", None)
        except Exception:
            _lvl = None
        if not _lvl:
            _lvl = getattr(getattr(settings, "BatchSettings", None), "opensim_log_level", None)
        # No level configured used to mean "do nothing" -- and on a console
        # (Git Bash) the fd swap is skipped too, so every Model construction
        # printed its printBasicInfo block to the terminal, six times per
        # exbiomec run. Default to "error": OpenSim still reports failures,
        # its [info] chatter does not. Set BatchSettings.opensim_log_level to
        # "info" to see it again.
        if not _lvl:
            _lvl = "error"
        _enum = {"off": osim.Logger.Level_Off, "critical": osim.Logger.Level_Critical,
                 "error": osim.Logger.Level_Error, "warn": osim.Logger.Level_Warn,
                 "warning": osim.Logger.Level_Warn, "info": osim.Logger.Level_Info,
                 "debug": osim.Logger.Level_Debug, "trace": osim.Logger.Level_Trace
                 }.get(str(_lvl).strip().lower())
        if _enum is not None:
            osim.Logger.setLevel(_enum)
        else:
            osim.Logger.setLevelString(str(_lvl).strip().lower())
    except Exception:
        pass

@_contextlib.contextmanager
def _osim_quiet_ctx():
    """Apply the configured OpenSim log level around an OpenSim tool. Tools RESET
    the logger to 'info' as they run, so we re-apply it BEFORE and AFTER. When the
    level is 'off', ALSO redirect C-level stdout (fd 1) to devnull for the duration
    — that swallows OpenSim's Model::printBasicInfo() block ("MODEL: ... coordinates
    ...") which is written to std::cout and bypasses the logger. stderr stays open
    (errors still surface); the Python log-file tee is unaffected."""
    _quiet_osim()
    # Quiet unless the project explicitly asks for OpenSim's chatter.
    #
    # This used to be opt-IN: redirect fd 1 only when
    # BatchSettings.opensim_log_level == "off". The gate resolves `settings`
    # through a sys.path insert that finds the project's settings.py only when
    # the process was started a particular way — so `python -c "from bioscout
    # import Session; ..."` from the project folder read no setting at all,
    # fell back to False, and OpenSim's printBasicInfo block came back four
    # times per trial. The same fragility already forced _quiet_model() to be
    # made unconditional; this is the other half of it.
    #
    # Now: quiet unless a level was explicitly set to something verbose. The
    # redirect covers fd 1 only, so errors on stderr still surface.
    _off = True
    try:
        _bs = getattr(getattr(settings, "BatchSettings", None), "opensim_log_level", None)
        if _bs is not None:
            _off = str(_bs).strip().lower() in ("off", "", "none")
    except Exception:
        _off = True
    if not _off:
        try:
            yield
        finally:
            _quiet_osim()
        return
    import sys as _sys
    try:
        _sys.stdout.flush()
    except Exception:
        pass
    # Swapping fd 1 for devnull silences OpenSim's C++ chatter, but it is only
    # safe when fd 1 is a real file or console. Under MINGW / Git Bash it is a
    # pty, and after the dup2 the NEXT ordinary print() raises
    # "OSError: [WinError 1] Incorrect function" -- from inside the wrapped
    # function, which makes it look like the OpenSim call failed when nothing
    # of the sort happened. If the swap cannot be done safely, skip it: noisy
    # output is a far smaller problem than a tool that appears to crash.
    # On Windows `sys.stdout` wraps a _WindowsConsoleIO bound to the CONSOLE
    # HANDLE, not to fd 1. Swapping fd 1 therefore leaves it writing to a
    # handle that is no longer a console, and the next ordinary print() dies
    # with "OSError: [WinError 1] Incorrect function" -- raised from inside the
    # wrapped function, so it reads as an OpenSim failure when nothing of the
    # sort happened. Only swap when stdout is NOT a console: a redirected file
    # or pipe survives it, and that is the case where the C++ chatter is worth
    # suppressing anyway.
    if _stdout_is_console():
        try:
            yield
        finally:
            _quiet_osim()
        return
    try:
        _saved = os.dup(1)
        _devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        try:
            yield
        finally:
            _quiet_osim()
        return
    _swapped = False
    try:
        try:
            os.dup2(_devnull, 1)
            _swapped = True
        except OSError:
            pass                      # keep the real stdout; just do not silence
        yield
    finally:
        try:
            _sys.stdout.flush()
        except Exception:
            pass
        if _swapped:
            try:
                os.dup2(_saved, 1)
            except OSError:
                pass
        for _fd in (_devnull, _saved):
            try:
                os.close(_fd)
            except OSError:
                pass
        _quiet_osim()

def _quiet_console(fn):
    """Decorator: run an OpenSim tool wrapper inside :func:`_osim_quiet_ctx`."""
    @_functools.wraps(fn)
    def _w(*a, **k):
        with _osim_quiet_ctx():
            return fn(*a, **k)
    return _w

def terminal_warnings(mode='off'):
    """Set OpenSim terminal warnings on or off."""
    if mode == 'off':
        osim.Logger.setLevelString('warning')
        print("OpenSim terminal warnings turned OFF.")
    elif mode == 'on':
        osim.Logger.setLevelString('info')
        print("OpenSim terminal warnings turned ON.")
    else:
        print("Invalid mode. Use 'on' or 'off'.")
