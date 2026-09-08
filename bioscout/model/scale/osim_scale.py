"""ScaleTool driving: build a scaled model, and place its markers.

Joins ``measurements.py`` (MeasurementSet construction) and ``model_scaler.py``
(the GUI's wrapper) in ``bioscout.model.scale``. Despite its name,
``place_markers_via_ik`` edits the model's marker placements -- it does not run
a simulation, which is why it is here and not under ``simulate``.

Split out of the old ``bioscout/utils/openSim.py`` (docs/RESTRUCTURE_PLAN.md,
stage 6) -- the code is unchanged, only its address.
"""
import os
import opensim as osim

try:                                    # the project's settings.py, if it has one
    from bioscout import settings
except Exception:                       # noqa: BLE001 - absent or mid-cycle
    settings = None
from bioscout.model.opensim_base import (_osim_quiet_ctx, _quiet_model,
                                         _quiet_osim)
from bioscout.model.edit.osim_ops import _strip_trailing_nulls


def scale_model_from_xml(setup_xml_path, generic_model_path, static_trc_path, scaled_model_path, mass=None):
    """
    Scale an OpenSim model using a pre-existing ScaleTool setup XML (preserving its
    MeasurementSet, MarkerPlacer IK tasks, etc.) while overriding the key file paths
    and optionally the subject mass.

    Args:
        setup_xml_path (str): Path to the ScaleTool setup XML file.
        generic_model_path (str): Path to the unscaled generic .osim model.
        static_trc_path (str): Path to the static trial TRC file.
        scaled_model_path (str): Absolute path for the output scaled .osim model.
        mass (float, optional): Subject mass in kg. Defaults to model total mass.
    """
    scale_tool = osim.ScaleTool(setup_xml_path)

    base_folder = os.path.dirname(setup_xml_path)

    if mass is not None:
        scale_tool.setSubjectMass(mass)

    # GenericModelMaker
    scale_tool.getGenericModelMaker().setModelFileName(generic_model_path)

    # ModelScaler
    model_scaler = scale_tool.getModelScaler()
    model_scaler.setApply(True)
    model_scaler.setMarkerFileName(os.path.basename(static_trc_path))
    model_scaler.setOutputModelFileName(os.path.relpath(scaled_model_path, base_folder))
    model_scaler.setOutputScaleFileName('scale_set.xml')

    # MarkerPlacer
    marker_placer = scale_tool.getMarkerPlacer()
    marker_placer.setApply(True)
    marker_placer.setMarkerFileName(os.path.basename(static_trc_path))
    marker_placer.setOutputModelFileName(os.path.relpath(scaled_model_path, base_folder))
    marker_placer.setOutputMarkerFileName('static_output.trc')

    # print scale tool setup xml
    os.chdir(base_folder)
    scale_tool.printToXML(os.path.join(base_folder, 'setup_scale.xml'))
    print(f"Modified ScaleTool setup saved to: {os.path.join(os.path.dirname(scaled_model_path), 'setup_scale.xml')}")

    output = scale_tool.run()
    
    if not output:
        print(f"Scaled model saved to: {scaled_model_path}")
    else:
        print("Error: Scaling failed. Check the ScaleTool setup and input files.")

    return scale_tool

def _sanitize_markerset_xml(src_path, skip_names, out_dir):
    """Write a copy of an OpenSim marker-set XML with markers removed that would
    crash ScaleTool's MarkerPlacer: those named in ``skip_names`` and any marker
    parented to ground (``<socket_parent_frame>`` referencing ground). Returns the
    sanitized file path, or None if nothing was removed."""
    import re
    txt = open(src_path, errors="replace").read()
    skipU = {str(s).upper() for s in (skip_names or set())}
    removed = []
    def _filt(m):
        name, body = m.group(1), m.group(2)
        pf = re.search(r'<socket_parent_frame>([^<]+)', body)
        frame = (pf.group(1) if pf else "").strip().lower()
        if name.upper() in skipU or frame.endswith("ground"):
            removed.append(name)
            return ""
        return m.group(0)
    new = re.sub(r'<Marker name="([^"]+)">(.*?)</Marker>\s*', _filt, txt, flags=re.S)
    if not removed:
        return None
    out = os.path.join(out_dir,
                       os.path.splitext(os.path.basename(src_path))[0] + "_scaleready.xml")
    with open(out, "w") as f:
        f.write(new)
    print(f"[scale] dropped unplaceable markers from marker set: {removed} -> {os.path.basename(out)}")
    return out

def scale_model(generic_opensim_model_path, static_trc_path, scaled_model_path, scale_setup_output_dir=None, mass=None, time_range=None, marker_set_file=None, linear_scaling=True, marker_placer=False, ik_weights=None, setup_xml_path=None, run=True):
    """
    Scale an OpenSim model using the ScaleTool based on static marker data from a TRC file.

    The ScaleTool has two independent stages, exposed here as booleans that map
    1:1 onto OpenSim's own ``ModelScaler`` and ``MarkerPlacer``:

      * ``linear_scaling`` (ModelScaler) — dimensional scaling from marker
        distances. Turn OFF for an already-personalised model (e.g. MRI/TPS
        geometry) so its segment sizes are NOT changed.
      * ``marker_placer`` (MarkerPlacer) — move the model's markers onto the
        subject's static-trial markers (with an IK pass). Useful even when
        ``linear_scaling`` is off, so markers line up for IK. Off by default
        because it is memory-heavy with 100+ marker sets.

    Combinations: both True = classic scale+placement; linear only = size but
    keep template markers; placer only = keep geometry, re-place markers
    (MRI case); both False = copy the model through unchanged.

    Args:
        scale_setup_output_dir: Directory where to save scale_setup.xml (defaults to scaled_model directory)
        ik_weights: ``{marker: weight}`` for the standalone marker-registration
            IK. A weight of 0 drops the marker from the pass entirely. Only
            used when ``marker_placer`` is on; ignored otherwise. Default None
            = every marker weighted 1.0, which is what this always did.
        setup_xml_path: Where to write the ScaleTool setup. Defaults to
            ``<scale_setup_output_dir>/scale_setup.xml``. This file is the
            record of what was actually applied — the MeasurementSet, the
            joint-centre-augmented TRC, the time range — and is the first thing
            to read when a scaled model looks wrong.
        run: False writes the setup and returns its path WITHOUT scaling. The
            setup references files under ``_temp_scaling/`` (the augmented TRC,
            the sanitised model), so that folder is kept in this mode — the
            setup is loadable in the OpenSim GUI as written.

    Returns:
        The setup XML path when ``run=False``; otherwise None.
    """
    import shutil as _shutil
    from bioscout.model.scale import measurements as _sm
    # Apply the configured OpenSim log level right here (lowercase — OpenSim
    # ignores "Error") so ScaleTool's geometry [warning] spam is quiet.
    try:
        _lvl = getattr(getattr(settings, "BatchSettings", None), "opensim_log_level", None)
        if _lvl:
            osim.Logger.setLevelString(str(_lvl).lower())
    except Exception:
        pass
    # Self-heal a corrupt generic: some TPS/warping tools pad the .osim with
    # trailing NUL bytes after </OpenSimDocument>. OpenSim loads it but ScaleTool's
    # MarkerPlacer then segfaults / throws "string too long". Strip the padding
    # (in place, with a .nulbak backup) so scaling works.
    generic_opensim_model_path = _strip_trailing_nulls(generic_opensim_model_path)
    # Neither stage requested → nothing for the ScaleTool to do; pass the model
    # through unchanged so downstream steps still find scaled_model_path.
    if not linear_scaling and not marker_placer:
        os.makedirs(os.path.dirname(scaled_model_path) or ".", exist_ok=True)
        if os.path.abspath(generic_opensim_model_path) != os.path.abspath(scaled_model_path):
            _shutil.copyfile(generic_opensim_model_path, scaled_model_path)
        print(f"[scale] linear_scaling=False, marker_placer=False → copied model "
              f"unchanged to: {scaled_model_path}")
        # "Unchanged" used to include the mass, so a model routed through this
        # branch kept whatever total mass its source had while every downstream
        # result was normalised by the subject's. Geometry still stays untouched.
        if mass is not None:
            try:
                _sm.set_total_mass(scaled_model_path, mass)
            except Exception as e:
                print(f"[scale] [WARNING] mass-only rescale failed: {e}")
        return
    model = _quiet_model(generic_opensim_model_path)
    state = model.initSystem()
    subject_mass = mass if mass is not None else model.getTotalMass(state)

    # MarkerPlacer runs an internal IK that SEGFAULTS on markers with no valid
    # placement — markers in BatchSettings.markers_to_skip and any marker rigidly
    # attached to ground (belt markers BL/BR). Strip them from a sanitized copy of
    # BOTH the model and the marker-set file, and scale from those, leaving the
    # user's originals untouched.
    try:
        from bioscout.utils import settings as _settings
        _skip = {str(s).upper() for s in
                 getattr(getattr(_settings, "BatchSettings", None), "markers_to_skip", []) or []}
    except Exception:
        _skip = set()
    _outdir = scale_setup_output_dir or os.path.dirname(scaled_model_path) or "."
    os.makedirs(_outdir, exist_ok=True)
    # Throwaway scaling intermediates (sanitized model/markerset, ScaleTool's
    # scale_setup.xml, the static-IK marker-registration .mot) live in a private
    # _temp_scaling/ subfolder that is removed on success — so they never clutter the
    # iteration folder. (Kept only if scaling raises, for debugging.)
    _tmp = os.path.join(_outdir, "_temp_scaling")
    os.makedirs(_tmp, exist_ok=True)
    generic_for_scaling = generic_opensim_model_path
    marker_set_for_scaling = marker_set_file
    _msd = model.updMarkerSet()
    _drop = []
    for _i in range(_msd.getSize()):
        _mk = _msd.get(_i)
        try:
            _fr = _mk.getParentFrame().getName().lower()
        except Exception:
            _fr = ""
        if _mk.getName().upper() in _skip or _fr == "ground":
            _drop.append((_i, _mk.getName()))
    if _drop:
        for _i, _ in sorted(_drop, reverse=True):
            _msd.remove(_i)
        model.finalizeConnections()
        generic_for_scaling = os.path.join(
            _tmp, os.path.splitext(os.path.basename(generic_opensim_model_path))[0] + "_scaleready.osim")
        model.printToXML(generic_for_scaling)
        print(f"[scale] dropped unplaceable markers from model: {[n for _, n in _drop]}")
    if marker_set_file and os.path.exists(marker_set_file):
        _san = _sanitize_markerset_xml(marker_set_file, _skip, _tmp)
        if _san:
            marker_set_for_scaling = _san

    # --- joint centres -----------------------------------------------------
    # ScaleTool measures DISTANCES BETWEEN MARKER PAIRS. The femur and tibia can
    # only be measured hip-to-knee-to-ankle, and a motion capture system cannot
    # see a joint centre — so the *WK virtual markers that markers_powerlifter.xml
    # puts on the body origins exist in every model but in NO TRC. Compute them
    # (Harrington hips, midpoint knees/ankles) into a scaling-only copy of the
    # static TRC. The ORIGINAL TRC is left untouched and is what marker
    # registration and every dynamic trial keep using.
    trc_for_scaling = static_trc_path
    if linear_scaling:
        try:
            trc_for_scaling = _sm.augment_static_trc(
                static_trc_path,
                os.path.join(_tmp, os.path.basename(static_trc_path).replace(".trc", "_jc.trc")))
        except Exception as e:
            print(f"[scale] [WARNING] could not add joint centres to the static TRC: {e}")
            trc_for_scaling = static_trc_path

    # Resolve time range from TRC if not provided
    storage = osim.Storage(trc_for_scaling)
    t0, t1 = (time_range[0], time_range[1]) if time_range else (storage.getFirstTime(), storage.getLastTime())
    osim_time_range = osim.ArrayDouble()
    osim_time_range.append(t0)
    osim_time_range.append(t1)

    scaleTool = osim.ScaleTool()
    scaleTool.setName("ModelScaling")
    scaleTool.setSubjectMass(subject_mass)

    # GenericModelMaker — sets the unscaled model (and optionally a marker set)
    gmm = scaleTool.getGenericModelMaker()
    gmm.setModelFileName(generic_for_scaling)
    if marker_set_for_scaling:
        gmm.setMarkerSetFileName(marker_set_for_scaling)

    # Determine where to save scale setup XML
    if scale_setup_output_dir is None:
        scale_setup_output_dir = os.path.dirname(scaled_model_path)
    os.makedirs(scale_setup_output_dir, exist_ok=True)

    # ModelScaler (dimensional scaling) — toggled by ``linear_scaling``.
    #
    # A default-constructed osim.ScaleTool() has an EMPTY MeasurementSet. OpenSim
    # accepts that without complaint: setApply(True) then scales every body by
    # 1.0 and only setSubjectMass() has any effect, so the output is generic
    # geometry wearing the subject's mass — a "scaled" model that is not scaled.
    # That silent failure is why this MeasurementSet is built and attached here,
    # and why verify_scaled() checks the result afterwards.
    modelScaler = scaleTool.getModelScaler()
    modelScaler.setApply(bool(linear_scaling))
    if linear_scaling:
        try:
            _mset, _rep, _skip_m = _sm.build_measurement_set(
                model, trc_for_scaling,
                model_markers=_sm.markerset_file_names(marker_set_for_scaling))
            if _mset.getSize() == 0:
                print("[scale] [ERROR] MeasurementSet is EMPTY — ScaleTool would apply a "
                      "scale factor of 1.0 to every body and return the generic model with "
                      "the subject's mass. Check the marker names above.")
            try:
                modelScaler.setMeasurementSet(_mset)
            except Exception:
                pass
            # getModelScaler()/getMeasurementSet() hand back C++ references through
            # SWIG, but that is an assumption worth checking rather than trusting:
            # if the set did not land, append into the tool's own set instead, and
            # if THAT does not stick, say so instead of scaling by 1.0 in silence.
            if modelScaler.getMeasurementSet().getSize() != _mset.getSize():
                _tgt = modelScaler.getMeasurementSet()
                for _i in range(_mset.getSize()):
                    _tgt.cloneAndAppend(_mset.get(_i))
            _n = modelScaler.getMeasurementSet().getSize()
            if _n != _mset.getSize():
                print(f"[scale] [ERROR] the ScaleTool kept {_n} of {_mset.getSize()} "
                      f"measurements — scaling would be wrong or absent. Aborting is safer "
                      f"than shipping a generic model named 'scaled'.")
                raise RuntimeError("MeasurementSet did not attach to the ScaleTool")
            try:
                modelScaler.setScalingOrder(osim.ArrayStr("measurements", 1))
            except Exception:
                pass
            print(f"[scale] ScaleTool holds {_n} measurements")
        except Exception as e:
            print(f"[scale] [ERROR] could not build the MeasurementSet: {e}")
            raise
    modelScaler.setMarkerFileName(trc_for_scaling)
    modelScaler.setTimeRange(osim_time_range)
    modelScaler.setOutputModelFileName(scaled_model_path)
    # Keep the computed scale factors OUT of the throwaway _temp_scaling folder:
    # this file is the record of exactly what was applied to each body, and it is
    # the first thing to read when a result looks wrong.
    modelScaler.setOutputScaleFileName(os.path.join(_outdir, 'scale_factors.xml'))

    # MarkerPlacer (place model markers onto static-trial markers) — toggled by
    # ``marker_placer``. Off by default (memory-heavy with 100+ markers). When
    # linear_scaling is off but this is on, it operates on the (unscaled) model —
    # the MRI case — and writes the final model to scaled_model_path.
    # MarkerPlacer: NEVER use ScaleTool's own C++ MarkerPlacer stage — its internal
    # IK throws a HARD SIGSEGV (uncatchable in Python, so a try/except cannot recover)
    # on some complex models (Catelli high-hip-flexion, MRI Lerner-knee). Instead
    # ScaleTool does DIMENSIONAL SCALING ONLY, then markers are registered by a
    # standalone IK pass (place_markers_via_ik) — the same MarkerPlacer algorithm,
    # done by hand, which is numerically equivalent, validates markers first, and is
    # crash-safe.
    markerPlacer = scaleTool.getMarkerPlacer()
    markerPlacer.setApply(False)

    # Write the setup BEFORE running. Written after, a crash leaves nothing to
    # read — which is exactly when you want it. This is a real ScaleTool setup:
    # OpenSim serialises it, so the OpenSim GUI opens it.
    _setup_out = setup_xml_path or os.path.join(_outdir, "scale_setup.xml")
    try:
        os.makedirs(os.path.dirname(_setup_out) or ".", exist_ok=True)
        scaleTool.printToXML(_setup_out)
        print(f"[scale] ScaleTool setup written: {_setup_out}")
    except Exception as e:
        print(f"[scale] [WARNING] could not write the ScaleTool setup: {e}")
        _setup_out = None

    if not run:
        # Deliberately NOT removing _temp_scaling: the setup points into it.
        print(f"[scale] run=False — setup written, nothing scaled. Its inputs "
              f"live in {_tmp}")
        return _setup_out

    print(f"[scale] linear_scaling={bool(linear_scaling)}, marker_placer={bool(marker_placer)} "
          f"(marker placement via standalone IK, not ScaleTool MarkerPlacer)")
    if linear_scaling:
        scaleTool.run()                           # dimensional scaling only -> scaled_model_path
    else:
        # MRI/TPS case: geometry is already personalised and must not be touched.
        # But with ModelScaler off, NOTHING ever applies the subject's mass, so the
        # model silently keeps the generic's — which is why the MRI variants were
        # carrying 75.34 kg while every result was normalised by the real body mass.
        # Copy the geometry through, then rescale mass and inertia alone.
        if os.path.abspath(generic_for_scaling) != os.path.abspath(scaled_model_path):
            _shutil.copyfile(generic_for_scaling, scaled_model_path)
        if mass is not None:
            try:
                _sm.set_total_mass(scaled_model_path, mass)
            except Exception as e:
                print(f"[scale] [WARNING] mass-only rescale failed: {e}")
    if marker_placer:
        # Register markers against the ORIGINAL TRC with the joint centres stripped
        # from the marker set: they are regression estimates, not measurements, and
        # must never pull the model's real markers around during the IK pass.
        _ms_place = _sm.marker_placement_markerset(marker_set_for_scaling, _tmp)
        place_markers_via_ik(scaled_model_path, static_trc_path, scaled_model_path,
                             marker_set_file=_ms_place, time_range=(t0, t1),
                             work_dir=_tmp, ik_weights=ik_weights)
    # Prove the model actually changed size. Without this the empty-MeasurementSet
    # failure is invisible: the file exists, is named scaled.osim, and every
    # downstream stage runs happily on generic geometry.
    if linear_scaling:
        try:
            _sm.verify_scaled(generic_for_scaling, scaled_model_path)
        except Exception as e:
            print(f"[scale] [WARNING] post-scaling verification failed: {e}")
    # scaling succeeded — drop the throwaway intermediates. The setup XML above
    # names two of them (the joint-centre-augmented TRC and, if markers were
    # dropped, the sanitised model), so those paths no longer resolve: the setup
    # is a RECORD of what ran, not a re-runnable file. Call with run=False to
    # get one that is.
    _shutil.rmtree(_tmp, ignore_errors=True)
    print(f"Scaled model saved to: {scaled_model_path}")

def place_markers_via_ik(model_path, static_trc, out_model_path,
                         marker_set_file=None, time_range=None, work_dir=None,
                         ik_weights=None):
    """Register a model's markers to the subject's STATIC pose WITHOUT ScaleTool's
    MarkerPlacer (which segfaults / throws bad_alloc on some complex models, e.g.
    the MRI/Lerner-knee model). Standard MarkerPlacer algorithm, done by hand:

      1. run a normal IK on the static trial (this path works where MarkerPlacer
         fails),
      2. move the model to the MEAN static pose,
      3. relocate each model marker to the averaged experimental marker position,
         expressed in that marker's parent frame.

    Writes the registered model to ``out_model_path``. Best-effort; on failure the
    base model is left as-is (markers un-registered)."""
    import numpy as _np
    _quiet_osim()
    model = _quiet_model(model_path)
    if marker_set_file and os.path.exists(marker_set_file):
        try:
            model.updateMarkerSet(osim.MarkerSet(model, marker_set_file))
        except Exception:
            pass
    state = model.initSystem()

    md = osim.MarkerData(static_trc)
    try:
        md.convertToUnits(osim.Units(osim.Units.Meters))     # -> metres to match the model
    except Exception:
        pass
    t0 = md.getStartFrameTime() if time_range is None else float(time_range[0])
    t1 = md.getLastFrameTime() if time_range is None else float(time_range[1])

    # 1) IK on the static trial
    _mot = (os.path.join(work_dir, os.path.splitext(os.path.basename(out_model_path))[0] + "_static_ik.mot")
            if work_dir else os.path.splitext(out_model_path)[0] + "_static_ik.mot")
    ik = osim.InverseKinematicsTool()
    # Marker weights for the registration pass. Without a task set every marker
    # is weighted 1.0, so a marker you know is badly placed pulls the static
    # pose exactly as hard as a reliable one — and the model's markers are then
    # registered to that pose.
    if ik_weights:
        try:
            _model_names = {model.getMarkerSet().get(_i).getName()
                            for _i in range(model.getMarkerSet().getSize())}
            _ts = osim.IKTaskSet()
            _used = _zero = 0
            for _n, _w in sorted(ik_weights.items()):
                if _n not in _model_names:
                    continue                      # in the TRC, not on the model
                _t = osim.IKMarkerTask()
                _t.setName(_n)
                _t.setWeight(float(_w))
                _t.setApply(float(_w) > 0)
                _ts.cloneAndAppend(_t)
                if float(_w) > 0:
                    _used += 1
                else:
                    _zero += 1
            if _ts.getSize():
                ik.set_IKTaskSet(_ts)
                print(f"[scale] marker registration IK: {_used} marker(s) weighted, "
                      f"{_zero} switched off")
        except Exception as e:
            print(f"[scale] [WARNING] could not apply marker weights to the "
                  f"registration IK ({e}); every marker weighted 1.0")
    ik.setModel(model)
    ik.setMarkerDataFileName(static_trc)
    ik.setStartTime(t0)
    ik.setEndTime(t1)
    ik.setOutputMotionFileName(_mot)
    # OpenSim defaults results_directory to './' (the PROCESS CWD) and
    # report_errors to True, so this registration pass used to drop
    # `_ik_marker_errors.sto` in whatever directory the run started from --
    # the project root -- overwritten by every model and session. Keep it
    # next to the model it belongs to.
    _ik_res = os.path.dirname(os.path.abspath(_mot))
    os.makedirs(_ik_res, exist_ok=True)
    try:
        ik.setResultsDir(_ik_res)
    except Exception:
        pass
    with _osim_quiet_ctx():
        ik.run()

    # 2) mean static pose
    sto = osim.Storage(_mot)
    try:
        if sto.isInDegrees():
            model.getSimbodyEngine().convertDegreesToRadians(sto)
    except Exception:
        pass
    cs = model.getCoordinateSet()
    for i in range(cs.getSize()):
        c = cs.get(i)
        arr = osim.ArrayDouble()
        try:
            sto.getDataColumn(c.getName(), arr)
            vals = [arr.getitem(k) for k in range(arr.getSize())]
        except Exception:
            vals = []
        if vals:
            try:
                c.setValue(state, float(_np.mean(vals)), False)
            except Exception:
                pass
    model.assemble(state)
    model.realizePosition(state)

    # 3) relocate markers to the averaged experimental positions
    ground = model.getGround()
    ms = model.updMarkerSet()
    nfr = md.getNumFrames()
    moved = 0
    for i in range(ms.getSize()):
        mk = ms.get(i)
        try:
            idx = md.getMarkerIndex(mk.getName())
        except Exception:
            idx = -1
        if idx < 0:
            continue
        acc = _np.zeros(3); n = 0
        for f in range(nfr):
            v = md.getFrame(f).getMarker(idx)
            x, y, z = v.get(0), v.get(1), v.get(2)
            if x == x:                                       # skip NaN
                acc += (x, y, z); n += 1
        if n == 0:
            continue
        p = acc / n
        try:
            pF = ground.findStationLocationInAnotherFrame(
                state, osim.Vec3(float(p[0]), float(p[1]), float(p[2])), mk.getParentFrame())
            mk.set_location(pF)
            moved += 1
        except Exception:
            pass
    model.finalizeConnections()
    model.printToXML(out_model_path)
    print(f"[scale] IK-based marker registration placed {moved}/{ms.getSize()} markers "
          f"-> {os.path.basename(out_model_path)}")
    return out_model_path
