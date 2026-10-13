"""
tools.py -- one OpenSim / CEINMS tool at a time, for the BioScout Web "Simulate" page.

The page sends the files for ONE tool (dropped into that tool's section) and the
model chosen from the list; the lab engine (web_engine.py) stores them under
<job>/tools/<tool>/in/ and runs ``run_tool`` in a child process. Every tool calls
the same bioscout function the pipeline uses, so a result here is a result there.

Anything a tool needs and was not dropped is taken, in this order:
  1. the output of an earlier tool in the same job (scaled model, IK .mot, GRF.xml,
     muscle-analysis folder, SO forces ...), so the sections chain without re-uploading;
  2. the template in bioscout/setup_files (IK task set, SO actuators, marker set ...);
  3. nothing -> the tool says which file is missing.

Outputs go to <job>/tools/<tool>/out/. ``describe()`` lists, per tool, the input
slots the page draws drop areas for.
"""
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                      # .../bioscout/bioscout
SETUP = os.path.join(PKG, "setup_files")
MODELS = os.path.join(PKG, "models")

# slot: (label, extensions, template file in setup_files or None, required)
TOOLS = {
    "scale": {
        "label": "Scale",
        "slots": {
            "static_trc": ("Static trial markers (.trc)", [".trc"], None, True),
            "markerset": ("Marker set (.xml)", [".xml"], "markers_pyCGM.xml", False),
            "scale_setup": ("Scale setup, measurement set (.xml)", [".xml"], "setup_scale.xml", False),
        },
        "options": {"mass": "Body mass (kg)", "aliases": "Marker aliases, e.g. LASI=LASIS RMALL=RLMA (only if your lab names differ)"},
    },
    "ik": {
        "label": "Inverse kinematics",
        "slots": {
            "motion_trc": ("Motion trial markers (.trc)", [".trc"], None, True),
            "taskset": ("IK task set (.xml)", [".xml"], "IK_task_set.xml", False),
            "model": ("Model (.osim) -- default: the scaled model", [".osim"], None, False),
        },
        "options": {"t0": "From (s)", "t1": "To (s)"},
    },
    "id": {
        "label": "Inverse dynamics",
        "slots": {
            "grf_mot": ("Ground reaction forces (.mot)", [".mot", ".sto"], None, True),
            "grf_xml": ("External loads (.xml) -- default: made from the .mot", [".xml"], None, False),
            "ik_mot": ("Joint angles (.mot) -- default: the IK result", [".mot", ".sto"], None, False),
            "model": ("Model (.osim) -- default: the scaled model", [".osim"], None, False),
        },
        "options": {},
    },
    "ma": {
        "label": "Muscle analysis",
        "slots": {
            "grf_mot": ("Ground reaction forces (.mot) -- default: from ID", [".mot", ".sto"], None, False),
            "ik_mot": ("Joint angles (.mot) -- default: the IK result", [".mot", ".sto"], None, False),
            "model": ("Model (.osim) -- default: the scaled model", [".osim"], None, False),
        },
        "options": {},
    },
    "rra": {
        "label": "Residual reduction analysis",
        "slots": {
            "ik_mot": ("Joint angles (.mot) -- default: the IK result", [".mot", ".sto"], None, False),
            "grf_mot": ("Ground reaction forces (.mot) -- default: from ID", [".mot", ".sto"], None, False),
            "grf_xml": ("External loads (.xml) -- default: from ID", [".xml"], None, False),
            "rra_setup": ("RRA setup template (.xml) -- default: built here", [".xml"], None, False),
            "rra_actuators": ("RRA actuators (.xml) -- default: built from the model", [".xml"], None, False),
            "rra_tasks": ("RRA tasks (.xml) -- default: every free coordinate", [".xml"], None, False),
            "model": ("Model (.osim) -- default: the scaled model", [".osim"], None, False),
        },
        "options": {"t0": "From (s) -- default: first force on a plate", "t1": "To (s) -- default: last force on a plate"},
    },
    "so": {
        "label": "Static optimisation",
        "slots": {
            "ik_mot": ("Joint angles (.mot) -- default: the IK result", [".mot", ".sto"], None, False),
            "grf_mot": ("Ground reaction forces (.mot) -- default: from ID", [".mot", ".sto"], None, False),
            "grf_xml": ("External loads (.xml) -- default: from ID", [".xml"], None, False),
            "actuators": ("Reserve actuators (.xml)", [".xml"], "actuators_so.xml", False),
            "so_setup": ("SO setup (.xml)", [".xml"], "setup_SO.xml", False),
            "model": ("Model (.osim) -- default: the scaled model", [".osim"], None, False),
        },
        "options": {"jra": "Also joint reaction loads (1 = yes)"},
    },
    "ceinms": {
        "label": "CEINMS",
        "slots": {
            "emg_mot": ("EMG envelopes, filtered and normalised (.mot/.sto) -- optional with the Python solver", [".mot", ".sto"], None, False),
            "ik_mot": ("Joint angles (.mot) -- default: the IK result", [".mot", ".sto"], None, False),
            "id_sto": ("Joint moments (.sto) -- default: the ID result", [".sto"], None, False),
            "ceinms_cfg": ("CEINMS execution config (.xml)", [".xml"], "ceinms_cfg.xml", False),
            "excitation_generator": ("Excitation generator (.xml)", [".xml"], "excitationGenerator.xml", False),
            "model": ("Model (.osim) -- default: the scaled model", [".osim"], None, False),
        },
        "options": {"solver": "Solver: auto, python (mew, runs anywhere) or exe (CEINMS.exe, Windows + EMG)",
                    "mass": "Body mass (kg) -- default: the one given to Scale",
                    "jra": "Also joint contact forces (1 = yes)"},
    },
}
ORDER = ["scale", "ik", "id", "ma", "rra", "so", "ceinms"]


def list_models(extra_dirs=()):
    """Generic models the page can choose from: bioscout/models and any extra folders."""
    out = []
    for d in [MODELS, *extra_dirs]:
        for p in sorted(glob.glob(os.path.join(d, "**", "*.osim"), recursive=True)):
            name = os.path.relpath(p, d).replace("\\", "/")
            if not any(m["name"] == name for m in out):
                out.append({"name": name, "path": p, "size": os.path.getsize(p)})
    return out


def describe():
    """Tools, slots and templates for the page (paths stripped)."""
    return [{"id": t, "label": TOOLS[t]["label"], "options": TOOLS[t]["options"],
             "slots": [{"id": s, "label": v[0], "ext": v[1], "template": v[2], "required": v[3]}
                       for s, v in TOOLS[t]["slots"].items()]} for t in ORDER]


# ---- where things are --------------------------------------------------------------
def tool_dir(job_dir, tool, kind):
    d = os.path.join(job_dir, "tools", tool, kind)
    os.makedirs(d, exist_ok=True)
    return d


def dropped(job_dir, tool, slot):
    hits = sorted(glob.glob(os.path.join(job_dir, "tools", tool, "in", slot + ".*")))
    return hits[0] if hits else None


def template(name):
    p = os.path.join(SETUP, name) if name else None
    return p if p and os.path.isfile(p) else None


def output_of(job_dir, tool, pattern):
    hits = sorted(glob.glob(os.path.join(job_dir, "tools", tool, "out", "**", pattern), recursive=True))
    return hits[0] if hits else None


def model_for(job_dir, tool, state):
    """Dropped model > scaled model from Scale > the generic model chosen on the page."""
    return (dropped(job_dir, tool, "model")
            or output_of(job_dir, "scale", "*_scaled.osim")
            or state.get("model_path"))


def ik_for(job_dir, tool):
    return dropped(job_dir, tool, "ik_mot") or output_of(job_dir, "ik", "ik.mot")


def grf_for(job_dir, tool):
    """(grf.mot, GRF.xml): this tool's drop, else the ones ID used; the xml is made when missing."""
    mot = dropped(job_dir, tool, "grf_mot") or dropped(job_dir, "id", "grf_mot")
    xml = dropped(job_dir, tool, "grf_xml") or dropped(job_dir, "id", "grf_xml") or output_of(job_dir, "id", "GRF.xml")
    if not xml and mot:
        # the .mot next to the .xml, as the pipeline keeps them: GRF.xml names its data file
        # relative to itself
        from bioscout.simulate.opensim import create_grf_xml
        out = tool_dir(job_dir, tool, "out")
        local = os.path.join(out, "grf.mot")
        if os.path.abspath(mot) != os.path.abspath(local):
            shutil.copy2(mot, local)
        xml = os.path.join(out, "GRF.xml")
        trc = dropped(job_dir, "ik", "motion_trc")
        create_grf_xml(grf_mot_path=local, output_xml_path=xml, marker_trc_path=trc)
        mot = local
    return mot, xml


def need(path, what):
    if not path or not os.path.isfile(path):
        raise SystemExit(f"[tools] missing: {what}")
    return path


def grf_window(mot, threshold=20.0):
    """(t0, t1) of the span where any plate carries more than `threshold` N vertically."""
    with open(mot) as f:
        lines = f.read().splitlines()
    h = next(i for i, l in enumerate(lines) if l.strip().lower() == "endheader")
    k = h + 1
    while not lines[k].strip():
        k += 1
    cols = lines[k].split()
    vy = [i for i, c in enumerate(cols) if c.endswith("_vy")]
    t0 = t1 = None
    for l in lines[k + 1:]:
        v = l.split()
        if len(v) < len(cols):
            continue
        if any(abs(float(v[i])) > threshold for i in vy):
            t = float(v[0]); t0 = t if t0 is None else t0; t1 = t
    return (t0, t1) if t0 is not None and t1 > t0 else None


# ---- RRA defaults built from the model ----------------------------------------------
def rra_defaults(model_path, out_dir):
    """actuators (pelvis residuals + a reserve per free coordinate) and tasks (every free
    coordinate), plus a setup template with the placeholders run_rra fills in."""
    import opensim as osim
    m = osim.Model(model_path)
    state = m.initSystem()
    # only independent, free coordinates: one driven by a constraint (a coupled patella
    # or knee translation) can be neither tracked nor actuated
    coords = [c for c in m.getCoordinateSet() if not c.get_locked() and not c.isDependent(state)]
    pelvis = next((b.getName() for b in m.getBodySet() if "pelvis" in b.getName().lower()), m.getBodySet().get(0).getName())
    act = ['<?xml version="1.0" encoding="UTF-8"?>', '<OpenSimDocument Version="40000">', "<ForceSet>", "<objects>"]
    for i, ax in enumerate(["X", "Y", "Z"]):
        d = ["1 0 0", "0 1 0", "0 0 1"][i]
        act.append(f'<PointActuator name="F{ax}"><body>{pelvis}</body><point>0 0 0</point><point_is_global>false</point_is_global>'
                   f'<direction>{d}</direction><force_is_global>true</force_is_global><optimal_force>4</optimal_force></PointActuator>')
        act.append(f'<TorqueActuator name="M{ax}"><bodyA>{pelvis}</bodyA><bodyB>ground</bodyB><axis>{d}</axis>'
                   f'<torque_is_global>true</torque_is_global><optimal_force>2</optimal_force></TorqueActuator>')
    tasks = ['<?xml version="1.0" encoding="UTF-8"?>', '<OpenSimDocument Version="40000">', '<CMC_TaskSet name="RRA">', "<objects>"]
    for c in coords:
        n = c.getName()
        if not n.startswith("pelvis"):
            act.append(f'<CoordinateActuator name="{n}_reserve"><coordinate>{n}</coordinate><optimal_force>300</optimal_force>'
                       f'<min_control>-1</min_control><max_control>1</max_control></CoordinateActuator>')
        tasks.append(f'<CMC_Joint name="{n}"><on>true</on><weight>1</weight><active>true false false</active>'
                     f'<kp>100</kp><kv>20</kv><coordinate>{n}</coordinate></CMC_Joint>')
    act += ["</objects>", "</ForceSet>", "</OpenSimDocument>"]
    tasks += ["</objects>", "</CMC_TaskSet>", "</OpenSimDocument>"]
    setup = """<?xml version="1.0" encoding="UTF-8"?>
<OpenSimDocument Version="40000">
<RRATool name="RRA">
<model_file>MODEL</model_file>
<replace_force_set>true</replace_force_set>
<force_set_files>ACTUATORS</force_set_files>
<results_directory>./</results_directory>
<output_precision>8</output_precision>
<initial_time>0</initial_time>
<final_time>1</final_time>
<solve_for_equilibrium_for_auxiliary_states>false</solve_for_equilibrium_for_auxiliary_states>
<maximum_number_of_integrator_steps>20000</maximum_number_of_integrator_steps>
<maximum_integrator_step_size>1</maximum_integrator_step_size>
<minimum_integrator_step_size>1e-08</minimum_integrator_step_size>
<integrator_error_tolerance>1.0000000000000001e-05</integrator_error_tolerance>
<external_loads_file>GRF_XML</external_loads_file>
<desired_kinematics_file>IK_MOT</desired_kinematics_file>
<task_set_file>TASKS</task_set_file>
<lowpass_cutoff_frequency>6</lowpass_cutoff_frequency>
<optimizer_algorithm>ipopt</optimizer_algorithm>
<numerical_derivative_step_size>1.0000000000000001e-05</numerical_derivative_step_size>
<optimization_convergence_tolerance>1.0000000000000001e-05</optimization_convergence_tolerance>
<adjust_com_to_reduce_residuals>true</adjust_com_to_reduce_residuals>
<initial_time_for_com_adjustment>-1</initial_time_for_com_adjustment>
<final_time_for_com_adjustment>-1</final_time_for_com_adjustment>
<adjusted_com_body>torso</adjusted_com_body>
<output_model_file>ADJUSTED_MODEL</output_model_file>
<use_verbose_printing>false</use_verbose_printing>
</RRATool>
</OpenSimDocument>
"""
    os.makedirs(out_dir, exist_ok=True)
    pa, pt, ps = (os.path.join(out_dir, n) for n in ("actuators_RRA.xml", "tasks_RRA.xml", "setup_RRA_template.xml"))
    open(pa, "w").write("\n".join(act))
    open(pt, "w").write("\n".join(tasks))
    open(ps, "w").write(setup)
    return pa, pt, ps


# ---- the tools ------------------------------------------------------------------------
def run_tool(job_dir, tool):
    """Runs inside the child process the engine starts. Reads <job>/tools/state.json."""
    sys.path.insert(0, os.path.dirname(PKG))
    st_path = os.path.join(job_dir, "tools", "state.json")
    state = json.load(open(st_path)) if os.path.isfile(st_path) else {}
    opts = state.get("options", {}).get(tool, {})
    out = tool_dir(job_dir, tool, "out")
    os.chdir(out)
    import bioscout.simulate.opensim as O

    if tool == "scale":
        from bioscout.model.scale.osim_scale import scale_model
        generic = need(state.get("model_path"), "a model chosen from the list")
        trc = need(dropped(job_dir, "scale", "static_trc"), "static trial .trc")
        mset = dropped(job_dir, "scale", "markerset") or template(TOOLS["scale"]["slots"]["markerset"][2])
        setup = dropped(job_dir, "scale", "scale_setup")
        name = os.path.splitext(os.path.basename(generic))[0]
        mass = float(opts["mass"]) if opts.get("mass") not in (None, "") else None
        aliases = {}
        for pair in str(opts.get("aliases") or "").replace(",", " ").split():
            if "=" in pair:
                a, b = pair.split("=", 1)
                aliases[a.strip()] = b.strip()
        scale_model(generic, trc, os.path.join(out, f"{name}_scaled.osim"), scale_setup_output_dir=out,
                    mass=mass, marker_set_file=mset, linear_scaling=True, marker_placer=True,
                    scale_tool=setup, marker_aliases=aliases or None)
        need(output_of(job_dir, "scale", "*_scaled.osim"), "scaled model (scaling produced none)")

    elif tool == "ik":
        model = need(model_for(job_dir, "ik", state), "a model (choose one, or run Scale)")
        trc = need(dropped(job_dir, "ik", "motion_trc"), "motion trial .trc")
        ts = dropped(job_dir, "ik", "taskset") or template("IK_task_set.xml")
        tr = None
        if opts.get("t0") not in (None, "") and opts.get("t1") not in (None, ""):
            tr = [float(opts["t0"]), float(opts["t1"])]
        setup = os.path.join(out, "setup_IK.xml")
        O.create_setup_IK(osim_modelPath=model, marker_trc=trc, ik_output=os.path.join(out, "ik.mot"),
                          taskSetPath=ts, time_range=tr, saveXMLPath=setup)
        O.run_ik(osim_modelPath=model, setup_xml=setup, resultsDir=out)
        need(output_of(job_dir, "ik", "ik.mot"), "ik.mot (IK produced none)")

    elif tool == "id":
        model = need(model_for(job_dir, "id", state), "a model")
        ik = need(ik_for(job_dir, "id"), "joint angles .mot (run IK or drop one)")
        _mot, xml = grf_for(job_dir, "id")
        need(xml, "ground reaction forces .mot")
        if not dropped(job_dir, "id", "grf_xml") and os.path.dirname(xml) != out:
            shutil.copy2(xml, os.path.join(out, "GRF.xml"))
        O.run_id(osimModelPath=model, ikOutputPath=ik, grfXmlPath=xml, setupXmlPath=os.path.join(out, "setup_ID.xml"))
        need(output_of(job_dir, "id", "inverse_dynamics.sto"), "inverse_dynamics.sto (ID produced none)")

    elif tool == "ma":
        model = need(model_for(job_dir, "ma", state), "a model")
        ik = need(ik_for(job_dir, "ma"), "joint angles .mot (run IK or drop one)")
        _mot, xml = grf_for(job_dir, "ma")
        need(xml, "ground reaction forces (drop a .mot here or run ID first)")
        O.run_ma(osim_modelPath=model, ik_output=ik, grf_xml=xml, results_dir=out)
        need(output_of(job_dir, "ma", "*MuscleAnalysis_Length.sto"), "muscle lengths (MA produced none)")

    elif tool == "rra":
        model = need(model_for(job_dir, "rra", state), "a model")
        ik = need(ik_for(job_dir, "rra"), "joint angles .mot")
        _mot, xml = grf_for(job_dir, "rra")
        need(xml, "ground reaction forces")
        pa, pt, ps = rra_defaults(model, os.path.join(out, "templates"))
        if opts.get("t0") not in (None, "") and opts.get("t1") not in (None, ""):
            tr = (float(opts["t0"]), float(opts["t1"]))
        else:
            # as the pipeline does: only the span with force on a plate, where the
            # residuals mean something
            tr = grf_window(_mot) if _mot else None
        print(f"[tools] RRA window: {tr}")
        res = O.run_rra(osim_modelPath=model, ik_output=ik, grf_xml=xml,
                        actuators=dropped(job_dir, "rra", "rra_actuators") or pa,
                        tasks=dropped(job_dir, "rra", "rra_tasks") or pt,
                        template_xml=dropped(job_dir, "rra", "rra_setup") or ps,
                        setup_xml=os.path.join(out, "setup_RRA.xml"), results_dir=out, time_range=tr)
        print("[tools] RRA:", res)

    elif tool == "so":
        model = need(model_for(job_dir, "so", state), "a model")
        ik = need(ik_for(job_dir, "so"), "joint angles .mot")
        _mot, xml = grf_for(job_dir, "so")
        need(xml, "ground reaction forces")
        act = dropped(job_dir, "so", "actuators") or template("actuators_so.xml")
        setup = dropped(job_dir, "so", "so_setup") or template("setup_SO.xml")
        local = os.path.join(out, "setup_SO.xml")
        shutil.copy2(setup, local)
        O.run_so(osim_modelPath=model, ik_output=ik, grf_xml=xml, setup_xml=local, actuators=act, resultsDir=out)
        if str(opts.get("jra", "1")) == "1":
            forces = output_of(job_dir, "so", "*StaticOptimization_force.sto")
            if forces:
                jsetup = os.path.join(out, "setup_JRA.xml")
                shutil.copy2(template("setup_JRA.xml"), jsetup)
                O.run_jra(osim_modelPath=model, ik_output=ik, grf_xml=xml, setup_xml=jsetup,
                          actuators=act, muscle_force_path=forces)

    elif tool == "ceinms":
        solver = str(opts.get("solver") or "auto").strip().lower()
        if solver == "auto":
            solver = "exe" if _ceinms_exe_ok() and dropped(job_dir, "ceinms", "emg_mot") else "python"
        if solver in ("python", "mew", "py"):
            run_ceinms_python(job_dir, state, out, opts)
        else:
            run_ceinms(job_dir, state, out)
    else:
        raise SystemExit(f"[tools] unknown tool {tool!r}")
    print(f"[tools] {tool} finished; outputs in {out}")


def _ceinms_exe_ok():
    """CEINMS.exe is a Windows program; anywhere else (the hosted engine) use mew."""
    if os.name != "nt":
        return False
    try:
        from bioscout.simulate.ceinms import commands as CX  # noqa: F401
        return True
    except Exception:
        return False


def run_ceinms_python(job_dir, state, out, opts):
    """CEINMS in Python (bioscout.simulate.mew): the same EMG-informed Hill-type
    solve, runs on any OS, and without EMG it falls back to the no-EMG tier
    instead of failing. Outputs use CEINMS's file names (MuscleForces.sto, ...)."""
    from bioscout.simulate.mew.pipeline import analyse_trial
    model = need(model_for(job_dir, "ceinms", state), "a model")
    ik = need(ik_for(job_dir, "ceinms"), "joint angles .mot (run IK or drop one)")
    mom = need(dropped(job_dir, "ceinms", "id_sto") or output_of(job_dir, "id", "inverse_dynamics.sto"),
               "joint moments (run ID)")
    trial = os.path.join(out, "trial")
    shutil.rmtree(trial, ignore_errors=True)
    os.makedirs(os.path.join(trial, "external_biomechanics"))
    shutil.copy2(ik, os.path.join(trial, "external_biomechanics", "joint_angles.mot"))
    shutil.copy2(mom, os.path.join(trial, "external_biomechanics", "inverse_dynamics.sto"))
    emg = dropped(job_dir, "ceinms", "emg_mot")
    if emg:
        os.makedirs(os.path.join(trial, "inputs"))
        shutil.copy2(emg, os.path.join(trial, "inputs", "emg_filtered_normalised.mot"))
    else:
        print("[tools] no EMG dropped: mew solves without EMG (moment tracking + effort)")
    if dropped(job_dir, "id", "grf_mot"):  # GRF.xml names grf.mot relative to itself
        grf, grf_xml = grf_for(job_dir, "id")
        os.makedirs(os.path.join(trial, "inputs"), exist_ok=True)
        shutil.copy2(grf, os.path.join(trial, "inputs", "grf.mot"))
        if grf_xml:
            shutil.copy2(grf_xml, os.path.join(trial, "inputs", "GRF.xml"))
    ma_len = output_of(job_dir, "ma", "*MuscleAnalysis_Length.sto")
    if ma_len:                       # moment arms from MA; else mew asks OpenSim
        shutil.copytree(os.path.dirname(ma_len), os.path.join(trial, "muscle_analysis"))
    so = output_of(job_dir, "so", "*StaticOptimization_force.sto")
    if so:                           # lets mew write its comparison vs SO
        os.makedirs(os.path.join(trial, "static_optimisation"))
        shutil.copy2(so, os.path.join(trial, "static_optimisation", "StaticOptimization_force.sto"))
    if template("setup_JRA.xml"):    # mew reuses the trial's JRA setup as its template
        os.makedirs(os.path.join(trial, "joint_contact_forces"))
        shutil.copy2(template("setup_JRA.xml"), os.path.join(trial, "joint_contact_forces", "setup_JRA.xml"))
    mass = opts.get("mass") or state.get("options", {}).get("scale", {}).get("mass")
    mass = float(mass) if mass not in (None, "") else None
    res = analyse_trial(trial, model, mass=mass, jcf=str(opts.get("jra", "1")) == "1",
                        plot=False, ceinms_compat=False, verbose=True)
    if res.get("jcf_error"):
        print(f"[tools] joint contact forces skipped: {res['jcf_error']}")
    # Flatten into out/ so the page lists them like any other tool's outputs.
    mew_dir = os.path.join(trial, "mew")
    for f in os.listdir(mew_dir):
        src = os.path.join(mew_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(out, f))


def run_ceinms(job_dir, state, out):
    """CEINMS execution on the uncalibrated subject built from the model, driven by the
    dropped EMG envelopes, with the IK, ID and MA of this job."""
    from bioscout.simulate.ceinms import configs as CC, commands as CX
    model = need(model_for(job_dir, "ceinms", state), "a model")
    ik = need(ik_for(job_dir, "ceinms"), "joint angles .mot (run IK or drop one)")
    mom = need(dropped(job_dir, "ceinms", "id_sto") or output_of(job_dir, "id", "inverse_dynamics.sto"), "joint moments (run ID)")
    ma_len = need(output_of(job_dir, "ma", "*MuscleAnalysis_Length.sto"), "muscle analysis (run MA)")
    ma_dir = os.path.dirname(ma_len)
    subj = os.path.join(out, "subjectUncalibrated.xml")
    CC.create_ceinms_model(osimModelPath=model, outputCEINMSModelPath=subj)
    emg = need(dropped(job_dir, "ceinms", "emg_mot"), "EMG envelopes (.mot/.sto)")
    exc = dropped(job_dir, "ceinms", "excitation_generator") or template("excitationGenerator.xml")
    inp = os.path.join(out, "inputData.xml")
    CC.create_input_data(MAFolder=ma_dir, excitationsFile=emg, motionFile=ik, externalTorquesFile=mom, output_path=inp)
    cfg = dropped(job_dir, "ceinms", "ceinms_cfg") or template("ceinms_cfg.xml")
    local_cfg = os.path.join(out, "ceinms_cfg.xml")
    shutil.copy2(cfg, local_cfg)
    setup = os.path.join(out, "setup_ceinms_exe.xml")
    with open(template("setup_ceinms_exe.xml")) as f:
        txt = f.read()
    import re
    for tag, val in (("subjectFile", subj), ("inputDataFile", inp), ("executionFile", local_cfg),
                     ("excitationGeneratorFile", exc), ("outputDirectory", os.path.join(out, "Execution"))):
        txt = re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}>{val}</{tag}>", txt, flags=re.S)
    open(setup, "w").write(txt)
    CX.executable(setupXML_path=setup)


if __name__ == "__main__":
    run_tool(sys.argv[1], sys.argv[2])
