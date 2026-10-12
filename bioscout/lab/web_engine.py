#!/usr/bin/env python3
"""
web_engine.py -- the lab engine: OpenSim for the BioScout Web lab demo.

A browser cannot run OpenSim. This is the computer that does: a small web
service on the lab PC that takes a student's static trial, motion trial and
force data, lays them out as an ordinary bioscout session, and runs the same
pipeline a researcher would -- export, scale, inverse kinematics + inverse
dynamics, static optimisation + joint reaction loads -- one step at a time,
handing each step's result back to the page to plot.

    python -m bioscout.lab.web_engine                    this PC only
    python -m bioscout.lab.web_engine --tunnel           + an https address phones can reach
    python -m bioscout.lab.web_engine --template D:\\course_project

It prints a link. Open it (or show it as a QR code) and the lab demo's
"OpenSim trial" card is connected.

What it will and will not do, none of it adjustable from the page:

  * It listens on 127.0.0.1 only. A browser on this PC can reach that from the
    https page; anything else gets in only through the tunnel you start.
  * Every request needs the session code printed at start-up. It changes each
    time the engine starts. Without it the service answers /health and nothing
    else.
  * Students upload DATA. The model, the marker set and the setup files are the
    ones in the template project on this PC (--template); a page cannot swap
    them, and cannot name a path.
  * One OpenSim step runs at a time, each in its own process. OpenSim changes
    the working directory and can take the interpreter down with it; a queue
    and a child process keep one student's bad trial from being everyone's.
  * Each student's files live in their own session folder under --work and are
    deleted after --keep-hours.

The service itself imports nothing but the standard library, so it starts
instantly and can be tested without OpenSim (--fake replays the template's
stored results). bioscout and OpenSim are imported only inside the child
process that runs a step.
"""
import argparse
import glob
import io
import json
import os
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

VERSION = 1
ITER = "lab"
SESSION = "s1"
STATIC, MOTION = "Static_01", "Motion_01"
# mew and CEINMS both balance their joint reactions with the SO reserve /
# residual columns, so both come after SO (bioscout Iteration.run).
STEPS = ["export", "scale", "ikid", "so", "mew", "ceinms"]
NEEDS = {"export": None, "scale": "export", "ikid": "scale", "so": "ikid", "mew": "so", "ceinms": "so"}
MAX_UPLOAD = 300 * 1024 * 1024
STEP_TIMEOUT_S = 45 * 60
APP_URL = "https://basgoncalves.github.io/bioscout-web/"
ORIGIN_OK = re.compile(r"^https://basgoncalves\.github\.io$|^https?://(localhost|127\.0\.0\.1)(:\d+)?$")
JOB_RE = re.compile(r"^L[0-9a-f]{8}$")

# What may be uploaded: kind -> (trial, the name it is stored under).
UPLOADS = {
    "static_c3d": (STATIC, "c3d"), "motion_c3d": (MOTION, "c3d"),
    "static_trc": (STATIC, "marker_experimental.trc"),
    "motion_trc": (MOTION, "marker_experimental.trc"),
    "motion_grf": (MOTION, "grf.mot"),
}
# A file is what its first bytes say it is, not what it was called.
MAGIC = {"c3d": lambda b: len(b) > 512 and b[1] == 0x50,
         "marker_experimental.trc": lambda b: b[:40].lstrip().lower().startswith(b"pathfiletype"),
         "grf.mot": lambda b: b"endheader" in b[:4000].lower()}

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


# ---- layout ------------------------------------------------------------------
def session_dir(work, job):
    return os.path.join(work, "simulations", job, SESSION)


def exp_dir(work, job, trial):
    return os.path.join(session_dir(work, job), "2_experimental", trial)


def c3d_dir(work, job):
    return os.path.join(session_dir(work, job), "1_c3dfiles")


def trial_out(work, job):
    return os.path.join(session_dir(work, job), "3_iterations", ITER, MOTION)


def model_dir(work, job):
    return os.path.join(work, "models", "personalised", job, SESSION)


RESULT_FILES = {
    "ik": ("external_biomechanics", "joint_angles.mot"),
    "ik_errors": ("external_biomechanics", "_ik_marker_errors.sto"),
    "id": ("external_biomechanics", "inverse_dynamics.sto"),
    "so": ("static_optimisation", "SO_StaticOptimization_force.sto"),
    "so_activation": ("static_optimisation", "SO_StaticOptimization_activation.sto"),
    "jra": ("joint_contact_forces", "Analyse_JRA_ReactionLoads_SO.sto"),
    "mew_jra": ("mew", "JRA_ReactionLoads.sto"),
    # The CEINMS reaction file has been named two ways across bioscout versions.
    "ceinms_jra": ("joint_contact_forces", ("Analyse_JRA_ReactionLoads_CEINMS.sto", "output_ceinms.sto",
                                            "*ReactionLoads*CEINMS*.sto", "*ceinms*ReactionLoads*.sto")),
}
# The files whose existence means a step really finished.
STEP_PROOF = {"ikid": ["ik", "id"], "so": ["so", "jra"], "mew": ["mew_jra"], "ceinms": ["ceinms_jra"]}
STEP_EXTRA = {"ikid": ["ik_errors"], "so": ["so_activation"]}


def write_session_yaml(work, job, mass, preset, trial_type="walking"):
    up = "../../../../.."
    text = f"""subject: {job}
session: '{SESSION}'
project_dir: ../../..
body_mass: {float(mass):.3f}
static_trial: {STATIC}
emg_map: {{}}
trials:
  {STATIC}:
    calibration: false
    emg_normalisation: false
    type: static
    side: both
  {MOTION}:
    calibration: false
    emg_normalisation: false
    type: {trial_type}
    side: both
iterations:
  {ITER}:
    model_generic: {up}/{preset['model']}
    model_scaled: {up}/models/personalised/{job}/{SESSION}/{ITER}_scaled.osim
    markerset: {up}/{preset['markerset']}
    linear_scaling: true
    marker_placer: true
    muscle_opt: false
    mvic_factor: 1.0
    label: Lab
    color: firebrick
    group: generic
# No EMG is uploaded, so CEINMS runs on the uncalibrated subject built from the
# scaled model (bioscout tags those outputs _uncal).
ceinms:
  calibrated: false
"""
    sd = session_dir(work, job)
    os.makedirs(os.path.join(sd, "3_iterations", ITER), exist_ok=True)
    with open(os.path.join(sd, "session.yaml"), "w", encoding="utf-8") as f:
        f.write(text)


# ---- reading OpenSim storage files ---------------------------------------------
def read_storage(path, max_rows=240):
    """An OpenSim .sto/.mot as {columns, time, data:{column:[...]}, inDegrees},
    thinned to at most max_rows rows. Standard library only."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    end = next((i for i, l in enumerate(lines) if l.strip().lower() == "endheader"), None)
    if end is None:
        raise ValueError("not an OpenSim storage file (no endheader)")
    deg = any(l.replace(" ", "").lower() == "indegrees=yes" for l in lines[:end])
    cols = lines[end + 1].strip().split("\t")
    if len(cols) < 2:
        cols = lines[end + 1].split()
    rows = []
    for l in lines[end + 2:]:
        p = l.split()
        if len(p) != len(cols):
            continue
        try:
            rows.append([float(x) for x in p])
        except ValueError:
            continue
    step = max(1, -(-len(rows) // max_rows))
    rows = rows[::step]
    data = {c: [round(r[i], 5) for r in rows] for i, c in enumerate(cols) if i > 0}
    return {"columns": cols[1:], "time": [round(r[0], 5) for r in rows], "data": data,
            "inDegrees": deg, "rows": len(rows)}


def read_scale_factors(path):
    out = []
    for sc in ET.parse(path).getroot().iter("Scale"):
        seg, val = sc.findtext("segment"), (sc.findtext("scales") or "").split()
        if seg and len(val) == 3 and "_geom_frame" not in seg and seg.strip() != "ground":
            out.append({"segment": seg.strip(), "scales": [round(float(v), 4) for v in val]})
    return out


# ---- the template project ------------------------------------------------------
def find_preset(project, model=None, markerset=None):
    """The one model + marker set this engine scales and solves with, as paths
    relative to the project folder."""
    def rel(p):
        return os.path.relpath(p, project).replace(os.sep, "/")
    if model:
        m = os.path.join(project, model)
    else:
        found = sorted(glob.glob(os.path.join(project, "generic models", "**", "*.osim"), recursive=True))
        m = found[0] if found else ""
    if markerset:
        k = os.path.join(project, "setupFiles", markerset)
    else:
        found = sorted(glob.glob(os.path.join(project, "setupFiles", "markers_*.xml")))
        k = found[0] if found else ""
    for what, p in (("generic model", m), ("marker set", k)):
        if not p or not os.path.isfile(p):
            raise SystemExit(f"[engine] no {what} in {project!r}. The template project needs "
                             f"'generic models/<...>.osim' and 'setupFiles/markers_<name>.xml' "
                             f"(or name them with --model / --markerset).")
    return {"model": rel(m), "markerset": rel(k)}


def find_example(template):
    """A static + a motion trial already exported in the template, to try the
    whole chain without uploading anything."""
    for sy in sorted(glob.glob(os.path.join(template, "simulations", "*", "*", "session.yaml"))):
        sd = os.path.dirname(sy)
        exp = os.path.join(sd, "2_experimental")
        with open(sy, encoding="utf-8", errors="replace") as f:
            text = f.read()
        st = re.search(r"^static_trial:\s*(\S+)", text, re.M)
        mass = re.search(r"^body_mass:\s*([0-9.]+)", text, re.M)
        static = st.group(1).strip("'\"") if st else STATIC
        if not os.path.isfile(os.path.join(exp, static, "marker_experimental.trc")):
            continue
        for t in sorted(os.listdir(exp)):
            td = os.path.join(exp, t)
            if t != static and os.path.isfile(os.path.join(td, "marker_experimental.trc")) \
                    and os.path.isfile(os.path.join(td, "grf.mot")):
                its = sorted(glob.glob(os.path.join(sd, "3_iterations", "*", t, "external_biomechanics",
                                                    "joint_angles.mot")))
                return {"session": sd, "static": static, "motion": t,
                        "mass": float(mass.group(1)) if mass else 75.0,
                        "stored": os.path.dirname(os.path.dirname(its[0])) if its else None}
    return None


def prepare_work(work, template):
    os.makedirs(os.path.join(work, "simulations"), exist_ok=True)
    for d in ("generic models", "setupFiles"):
        src, dst = os.path.join(template, d), os.path.join(work, d)
        if os.path.isdir(src) and not os.path.isdir(dst):
            shutil.copytree(src, dst)


def purge_old(work, keep_hours):
    root = os.path.join(work, "simulations")
    for j in os.listdir(root) if os.path.isdir(root) else []:
        p = os.path.join(root, j)
        if JOB_RE.match(j) and time.time() - os.path.getmtime(p) > keep_hours * 3600:
            shutil.rmtree(p, ignore_errors=True)
            shutil.rmtree(os.path.join(work, "models", "personalised", j), ignore_errors=True)


# ---- one step, in a child process ------------------------------------------------
def run_step(sd, step):
    """Runs inside the child. Imports bioscout (and with it OpenSim)."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    from bioscout.session import Session
    s = Session(sd)
    if step == "export":
        from bioscout.session.layout import c3d_root, experimental_dir
        have = [os.path.splitext(os.path.basename(p))[0]
                for p in glob.glob(os.path.join(c3d_root(sd), "*.c3d"))]
        if have:
            s.export(trials=have, replace=True, normalise=False, detect=False)
        mexp = experimental_dir(sd, MOTION)
        grf, trc = os.path.join(mexp, "grf.mot"), os.path.join(mexp, "marker_experimental.trc")
        if os.path.isfile(grf) and not os.path.isfile(os.path.join(mexp, "GRF.xml")):
            from bioscout.simulate.opensim import create_grf_xml
            create_grf_xml(grf_mot_path=grf, output_xml_path=os.path.join(mexp, "GRF.xml"),
                           marker_trc_path=trc if os.path.isfile(trc) else None)
        for t in (STATIC, MOTION):
            if not os.path.isfile(os.path.join(experimental_dir(sd, t), "marker_experimental.trc")):
                raise SystemExit(f"[engine] no markers were produced for {t}")
    elif step == "scale":
        if not s.iteration(ITER).scale_model(replace=True, muscle_opt=False):
            raise SystemExit("[engine] scaling produced no model")
    elif step == "ikid":
        res = s.iteration(ITER).run(trials=[MOTION], do_exbiomec=True, replace=True)
        if MOTION not in (res or {}).get("exbiomec", []):
            raise SystemExit("[engine] inverse kinematics / inverse dynamics did not finish")
    elif step == "so":
        res = s.iteration(ITER).run(trials=[MOTION], do_muscle_analysis=True, do_so=True, replace=True)
        if MOTION not in (res or {}).get("so", []):
            raise SystemExit("[engine] static optimisation / joint reactions did not finish")
    elif step == "mew":
        res = s.iteration(ITER).run(trials=[MOTION], do_mew=True, replace=True, mew_opts={"plot": False})
        if MOTION not in (res or {}).get("mew", []):
            raise SystemExit("[engine] mew did not finish")
    elif step == "ceinms":
        res = s.iteration(ITER).run(trials=[MOTION], do_ceinms=True, calibrate=False, replace=True)
        if MOTION not in (res or {}).get("ceinms", []):
            raise SystemExit("[engine] CEINMS did not finish")
    else:
        raise SystemExit(f"[engine] unknown step {step!r}")


# ---- the service -------------------------------------------------------------------
class Engine:
    def __init__(self, work, template, preset, example, code, fake=False):
        self.work, self.template, self.preset = work, template, preset
        self.example, self.code, self.fake = example, code, fake
        self.jobs = {}
        self.lock = threading.Lock()
        self.q = queue.Queue()
        self.waiting = []            # job ids, in the order they will run
        self.running = None
        threading.Thread(target=self._worker, daemon=True).start()

    # -- jobs
    def new_job(self):
        job = "L" + secrets.token_hex(4)
        st = {"id": job, "created": time.time(), "mass": 75.0, "files": {}, "example": False,
              "steps": {s: {"state": "idle"} for s in STEPS}}
        os.makedirs(session_dir(self.work, job), exist_ok=True)
        with self.lock:
            self.jobs[job] = st
        write_session_yaml(self.work, job, st["mass"], self.preset)
        return st

    def job(self, job):
        if not JOB_RE.match(job or ""):
            return None
        with self.lock:
            return self.jobs.get(job)

    def public(self, st):
        out = json.loads(json.dumps(st))
        with self.lock:
            waiting = list(self.waiting)
        for name, sp in out["steps"].items():
            if sp["state"] == "queued":
                sp["ahead"] = (waiting.index(st["id"]) if st["id"] in waiting else 0) \
                    + (1 if self.running and self.running != st["id"] else 0)
            if sp["state"] in ("running", "error", "done"):
                sp["log"] = self.log_tail(st["id"], name)
        out["ready"] = self.ready(st)
        return out

    def ready(self, st):
        f = st["files"]
        return {"static": bool(st["example"] or "static_c3d" in f or "static_trc" in f),
                "motion": bool(st["example"] or "motion_c3d" in f or ("motion_trc" in f and "motion_grf" in f))}

    def set_mass(self, st, mass):
        mass = float(mass)
        if not 20 <= mass <= 250:
            raise ValueError("body mass must be between 20 and 250 kg")
        st["mass"] = mass
        write_session_yaml(self.work, st["id"], mass, self.preset)
        self.invalidate(st, "scale")

    def invalidate(self, st, from_step):
        """A changed input makes every later result stale."""
        for s in STEPS[STEPS.index(from_step):]:
            if st["steps"][s]["state"] in ("done", "error"):
                st["steps"][s] = {"state": "idle"}

    def save_upload(self, st, kind, body):
        trial, name = UPLOADS[kind]
        if not MAGIC[name](body):
            raise ValueError(f"that does not look like a {name.split('.')[-1].upper()} file")
        if name == "c3d":
            d = c3d_dir(self.work, st["id"])
            path = os.path.join(d, trial + ".c3d")
        else:
            d = exp_dir(self.work, st["id"], trial)
            path = os.path.join(d, name)
        os.makedirs(d, exist_ok=True)
        if name == "grf.mot":
            try:
                os.remove(os.path.join(d, "GRF.xml"))
            except OSError:
                pass
        with open(path, "wb") as f:
            f.write(body)
        st["files"][kind] = len(body)
        st["example"] = False
        self.invalidate(st, "export")

    def use_example(self, st):
        ex = self.example
        if not ex:
            raise ValueError("this engine has no example data")
        for src_t, dst_t in ((ex["static"], STATIC), (ex["motion"], MOTION)):
            d = exp_dir(self.work, st["id"], dst_t)
            os.makedirs(d, exist_ok=True)
            for n in ("marker_experimental.trc", "grf.mot", "GRF.xml"):
                p = os.path.join(ex["session"], "2_experimental", src_t, n)
                if os.path.isfile(p):
                    shutil.copy2(p, os.path.join(d, n))
        shutil.rmtree(c3d_dir(self.work, st["id"]), ignore_errors=True)
        st["files"], st["example"] = {}, True
        self.set_mass(st, ex["mass"])
        self.invalidate(st, "export")
        return st

    # -- running
    def start(self, st, step):
        if step not in STEPS:
            raise ValueError("unknown step")
        need = NEEDS[step]
        if need and st["steps"][need]["state"] != "done":
            raise ValueError(f"run {need} first")
        r = self.ready(st)
        if not (r["static"] and r["motion"]):
            raise ValueError("upload the static and the motion trial first")
        if st["steps"][step]["state"] in ("queued", "running"):
            return
        self.invalidate(st, step)
        st["steps"][step] = {"state": "queued", "queued": time.time()}
        with self.lock:
            self.waiting.append(st["id"])
        self.q.put((st["id"], step))

    def log_path(self, job, step):
        return os.path.join(session_dir(self.work, job), "logs", f"engine_{step}.log")

    def log_tail(self, job, step, n=25):
        try:
            with open(self.log_path(job, step), "r", encoding="utf-8", errors="replace") as f:
                lines = [l.rstrip() for l in f.read().splitlines() if l.strip()]
            # Paths on this PC are nobody else's business.
            return [l.replace(self.work, "<work>").replace(REPO_ROOT, "<bioscout>")[:300] for l in lines[-n:]]
        except OSError:
            return []

    def _worker(self):
        while True:
            job, step = self.q.get()
            with self.lock:
                if job in self.waiting:
                    self.waiting.remove(job)
            st = self.job(job)
            if not st or st["steps"][step]["state"] != "queued":
                continue
            self.running = job
            sp = st["steps"][step] = {"state": "running", "started": time.time()}
            ok, err = False, None
            try:
                os.makedirs(os.path.dirname(self.log_path(job, step)), exist_ok=True)
                with open(self.log_path(job, step), "w", encoding="utf-8") as log:
                    if self.fake:
                        self._fake(job, step, log)
                        rc = 0
                    else:
                        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
                        rc = subprocess.run(
                            [sys.executable, os.path.abspath(__file__), "--run-step",
                             session_dir(self.work, job), step],
                            stdout=log, stderr=subprocess.STDOUT, cwd=self.work, env=env,
                            timeout=STEP_TIMEOUT_S).returncode
                missing = [k for k in STEP_PROOF.get(step, []) if not os.path.isfile(self.result_path(job, k))]
                if step == "scale" and not self.scaled_model(job):
                    missing.append("scaled model")
                ok = rc == 0 and not missing
                if not ok:
                    err = f"exit code {rc}" if rc else "no output: " + ", ".join(missing)
            except subprocess.TimeoutExpired:
                err = f"stopped after {STEP_TIMEOUT_S // 60} minutes"
            except Exception as e:                     # noqa: BLE001 -- reported, not raised
                err = f"{type(e).__name__}: {e}"
            sp.update(state="done" if ok else "error", ended=time.time(),
                      seconds=round(time.time() - sp["started"], 1))
            if err:
                sp["error"] = err
            print(f"[engine] {job} {step}: {'done' if ok else 'FAILED (' + str(err) + ')'} "
                  f"in {sp['seconds']} s", flush=True)
            self.running = None

    def _fake(self, job, step, log):
        """Replay the template's stored results instead of computing them."""
        ex = self.example
        if not ex or not ex.get("stored"):
            raise RuntimeError("--fake needs a template with stored results")
        time.sleep(0.4)
        log.write(f"[fake] replaying stored {step} from the template project\n")
        if step == "scale":
            hits = sorted(glob.glob(os.path.join(self.template, "models", "personalised", "*", "*", "*_scaled.osim")))
            os.makedirs(model_dir(self.work, job), exist_ok=True)
            if hits:
                shutil.copy2(hits[0], os.path.join(model_dir(self.work, job), f"{ITER}_scaled.osim"))
                sf = os.path.join(os.path.dirname(hits[0]), "scale_factors.xml")
                if os.path.isfile(sf):
                    shutil.copy2(sf, os.path.join(model_dir(self.work, job), "scale_factors.xml"))
        for key in STEP_PROOF.get(step, []) + STEP_EXTRA.get(step, []):
            folder, names = RESULT_FILES[key]
            name = names if isinstance(names, str) else names[0]
            src = os.path.join(ex["stored"], folder, name)
            if not os.path.isfile(src) and not isinstance(names, str):
                hits = [h for n in names for h in sorted(glob.glob(os.path.join(ex["stored"], folder, n)))]
                src = hits[0] if hits else src
            if os.path.isfile(src):
                dst = self.result_path(job, key)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

    # -- results
    def result_path(self, job, key):
        folder, names = RESULT_FILES[key]
        base = os.path.join(trial_out(self.work, job), folder)
        if isinstance(names, str):
            return os.path.join(base, names)
        for n in names:                     # first that exists; else the first name
            hits = sorted(glob.glob(os.path.join(base, n)))
            if hits:
                return hits[0]
        return os.path.join(base, names[0])

    def scaled_model(self, job):
        hits = sorted(glob.glob(os.path.join(model_dir(self.work, job), "*.osim")))
        pref = [h for h in hits if os.path.basename(h) == f"{ITER}_scaled.osim"]
        return (pref or hits or [None])[0]

    def result(self, st, what):
        job = st["id"]
        if what == "scale":
            m = self.scaled_model(job)
            if not m:
                raise FileNotFoundError("no scaled model yet")
            sf = sorted(glob.glob(os.path.join(model_dir(self.work, job), "*scale*factor*.xml")))
            return {"model": os.path.basename(m), "mass": st["mass"],
                    "factors": read_scale_factors(sf[0]) if sf else []}
        if what not in RESULT_FILES:
            raise FileNotFoundError("unknown result")
        p = self.result_path(job, what)
        if not os.path.isfile(p):
            raise FileNotFoundError("no such result yet")
        out = read_storage(p)
        out["mass"] = st["mass"]
        return out

    def bundle(self, st):
        """Everything this trial produced, as a zip the student keeps."""
        job, buf = st["id"], io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            m = self.scaled_model(job)
            if m:
                z.write(m, "model/" + os.path.basename(m))
            for key, (folder, _n) in RESULT_FILES.items():
                p = self.result_path(job, key)
                if os.path.isfile(p):
                    z.write(p, f"{folder}/{os.path.basename(p)}")
            for t in (STATIC, MOTION):
                for n in ("marker_experimental.trc", "grf.mot", "GRF.xml"):
                    p = os.path.join(exp_dir(self.work, job, t), n)
                    if os.path.isfile(p):
                        z.write(p, f"experimental/{t}/{n}")
        return buf.getvalue()


def make_handler(engine):
    class H(BaseHTTPRequestHandler):
        server_version = "BioScoutLabEngine/" + str(VERSION)

        def log_message(self, *a):          # one line per step is enough; see the worker
            pass

        def _cors(self):
            origin = self.headers.get("Origin", "")
            if ORIGIN_OK.match(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "content-type, x-lab-code")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Cache-Control", "no-store")

        def _send(self, status, body, ctype="application/json", extra=None):
            data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _fail(self, status, code, message):
            self._send(status, {"error": code, "message": message})

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _authed(self, q):
            given = self.headers.get("X-Lab-Code") or (q.get("code") or [""])[0]
            return secrets.compare_digest(str(given), engine.code)

        def _route(self, method):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            parts = [p for p in u.path.split("/") if p]
            if method == "GET" and parts == ["health"]:
                return self._send(200, {"ok": True, "name": "bioscout-lab-engine", "version": VERSION,
                                        "fake": engine.fake, "example": bool(engine.example),
                                        "model": os.path.basename(engine.preset["model"]),
                                        "markerset": os.path.basename(engine.preset["markerset"]),
                                        "steps": STEPS,
                                        "authed": self._authed(q)})
            if not self._authed(q):
                return self._fail(401, "bad_code", "wrong or missing session code")
            if method == "POST" and parts == ["api", "job"]:
                return self._send(200, engine.public(engine.new_job()))
            if len(parts) < 3 or parts[:2] != ["api", "job"]:
                return self._fail(404, "not_found", "no such address")
            st = engine.job(parts[2])
            if not st:
                return self._fail(404, "no_job", "that trial is not on this engine (it may have restarted)")
            rest = parts[3:]
            try:
                if method == "GET" and not rest:
                    return self._send(200, engine.public(st))
                if method == "GET" and rest == ["result"]:
                    return self._send(200, engine.result(st, (q.get("what") or [""])[0]))
                if method == "GET" and rest == ["bundle"]:
                    return self._send(200, engine.bundle(st), "application/zip",
                                      {"Content-Disposition": f'attachment; filename="opensim_{st["id"]}.zip"'})
                if method == "POST":
                    n = int(self.headers.get("Content-Length") or 0)
                    if n > MAX_UPLOAD:
                        return self._fail(413, "too_big", "file too large")
                    body = self.rfile.read(n) if n else b""
                    if rest == ["file"]:
                        kind = (q.get("kind") or [""])[0]
                        if kind not in UPLOADS:
                            return self._fail(400, "bad_kind", "unknown file kind")
                        engine.save_upload(st, kind, body)
                    elif rest == ["mass"]:
                        engine.set_mass(st, json.loads(body or b"{}").get("mass"))
                    elif rest == ["example"]:
                        engine.use_example(st)
                    elif rest == ["run"]:
                        engine.start(st, json.loads(body or b"{}").get("step"))
                    else:
                        return self._fail(404, "not_found", "no such address")
                    return self._send(200, engine.public(st))
            except FileNotFoundError as e:
                return self._fail(404, "no_result", str(e))
            except (ValueError, TypeError, KeyError) as e:
                return self._fail(400, "bad_request", str(e))
            return self._fail(404, "not_found", "no such address")

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")
    return H


def start_tunnel(port, on_url):
    """cloudflared quick tunnel: an https address that forwards to this PC."""
    exe = shutil.which("cloudflared")
    if not exe:
        print("[engine] --tunnel needs cloudflared on the PATH "
              "(winget install Cloudflare.cloudflared). Running for this PC only.")
        return None
    proc = subprocess.Popen([exe, "tunnel", "--url", f"http://127.0.0.1:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def pump():
        seen = False
        for line in proc.stdout:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m and not seen:
                seen = True
                on_url(m.group(0))
    threading.Thread(target=pump, daemon=True).start()
    return proc


def student_link(engine_url, code):
    return f"{APP_URL}?lab=1&engine={quote(engine_url, safe='')}&code={code}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="OpenSim engine for the BioScout Web lab demo")
    ap.add_argument("--run-step", nargs=2, metavar=("SESSION_DIR", "STEP"), help=argparse.SUPPRESS)
    ap.add_argument("--port", type=int, default=8771)
    ap.add_argument("--work", default=os.path.join(os.path.expanduser("~"), "bioscout_lab_engine"),
                    help="where students' trials are kept while they work")
    ap.add_argument("--template", default=os.path.join(REPO_ROOT, "example_data", "orthoload"),
                    help="project folder holding 'generic models/' and 'setupFiles/' (and, optionally, example data)")
    ap.add_argument("--model", help="generic model, relative to the template (default: the first .osim found)")
    ap.add_argument("--markerset", help="marker set file name in setupFiles/ (default: the first markers_*.xml)")
    ap.add_argument("--code", help="session code (default: a new random one)")
    ap.add_argument("--keep-hours", type=float, default=24.0)
    ap.add_argument("--tunnel", action="store_true", help="also open an https address for phones (needs cloudflared)")
    ap.add_argument("--fake", action="store_true", help="replay the template's stored results instead of running OpenSim")
    a = ap.parse_args(argv)

    if a.run_step:
        run_step(*a.run_step)
        return 0

    template = os.path.abspath(a.template)
    if not os.path.isdir(template):
        raise SystemExit(f"[engine] template project not found: {template}")
    work = os.path.abspath(a.work)
    prepare_work(work, template)
    purge_old(work, a.keep_hours)
    preset = find_preset(work, a.model, a.markerset)
    example = find_example(template)
    code = a.code or f"{secrets.randbelow(10**6):06d}"
    engine = Engine(work, template, preset, example, code, fake=a.fake)
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(engine))
    local = f"http://127.0.0.1:{a.port}"
    print(f"[engine] BioScout lab engine v{VERSION}{'  (FAKE: replaying stored results)' if a.fake else ''}")
    print(f"[engine] model      {preset['model']}")
    print(f"[engine] marker set {preset['markerset']}")
    print(f"[engine] example    {'yes: ' + example['motion'] if example else 'none in the template'}")
    print(f"[engine] trials in  {work}")
    print(f"[engine] session code  {code}")
    print(f"[engine] on this PC:   {student_link(local, code)}")
    tunnel = None
    if a.tunnel:
        tunnel = start_tunnel(a.port, lambda url: print(f"[engine] for phones:   {student_link(url, code)}", flush=True))
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[engine] stopped")
    finally:
        if tunnel:
            tunnel.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
