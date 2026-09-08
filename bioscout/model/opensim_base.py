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

def _quiet_model(arg):
    """``osim.Model(arg)`` with its printBasicInfo() dump suppressed.

    Constructing a Model writes a fixed block to std::cout from C++::

                   MODEL: 021
             coordinates: 39
                  forces: 97
             ...
        misc modelcomponents: 0

    It bypasses OpenSim's logger, so BatchSettings.opensim_log_level cannot
    touch it, and it bypasses sys.stdout, so the _Tee log filter never sees it
    either. Only a file-descriptor level redirect stops it.

    The redirect here is UNCONDITIONAL — deliberately not gated on
    opensim_log_level like _osim_quiet_ctx(). That gate reads `settings`, which
    openSim.py resolves via a sys.path insert of its own directory, so which
    module it lands on depends on how the process was started; the block kept
    leaking through as a result. printBasicInfo carries no diagnostic value, and
    fd 2 (stderr) stays open throughout, so genuine OpenSim errors still surface.
    """
    import sys as _sys
    try:
        _sys.stdout.flush()
    except Exception:
        pass
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
        if not _lvl:
            return
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
    _console = False
    try:
        _raw = getattr(getattr(_sys.stdout, "buffer", None), "raw", None)
        _console = (os.name == "nt"
                    and (type(_raw).__name__ == "_WindowsConsoleIO"
                         or _sys.stdout.isatty()))
    except Exception:                                        # noqa: BLE001
        _console = os.name == "nt"
    if _console:
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
