"""Fire a multi-subject analysis into the background and give the shell back.

    bioscout run 009 010 011 --iteration gpk --trial Run_baseline1,SJ1

prints the header and the log paths, then returns immediately: one detached
worker runs the stages for each subject in turn, writing each subject's output
to its own log. Nothing is streamed to the terminal, because a run of this
length outlives the terminal it was started from -- the logs are the record.

    bioscout run --status          what is running, what finished, how long
    bioscout run --status JOB_ID   the stage-by-stage detail of one job

Implementation note: the worker is this same module re-invoked with --worker,
detached from the launching shell (``start_new_session`` on POSIX,
DETACHED_PROCESS on Windows), so closing the terminal does not kill the run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

#: the stages a run can do, in the order they must happen
STAGES = ("export", "classify", "scale", "exbiomec", "ma", "so", "ceinms")
DEFAULT_STAGES = ("export", "classify", "scale", "exbiomec", "ma", "so")


def _session_stage(stage: str) -> bool:
    return stage in ("export", "classify", "scale")


def _command(stage, session, iteration, trials, replace):
    """The argv for one stage, as the CLI would be typed."""
    exe = [sys.executable, "-m", "bioscout.cli"]
    if stage in ("export", "classify"):
        return exe + ["session", stage, session]
    if stage == "scale":
        out = exe + ["session", "scale", session, "--iteration", iteration]
        return out + ["--replace"] if replace else out
    out = exe + ["simulate", stage, session, "--iteration", iteration]
    if trials:
        out += ["--trial", trials]
    return out + ["--replace"] if replace else out


def _job_dir(project: Path, stamp: str) -> Path:
    d = project / "logs" / "batch" / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# the worker: runs the plan, writes the logs, keeps status.json current
# --------------------------------------------------------------------------- #
def _run_worker(job_path: str) -> int:
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    st_path = Path(job["status"])
    status = json.loads(st_path.read_text(encoding="utf-8"))
    status["state"] = "running"
    status["started"] = datetime.now().isoformat(timespec="seconds")
    _write(st_path, status)

    bad = 0
    for item in job["items"]:
        rec = status["subjects"][item["subject"]]
        rec["state"] = "running"
        rec["started"] = datetime.now().isoformat(timespec="seconds")
        _write(st_path, status)
        t0 = time.time()
        with open(item["log"], "w", encoding="utf-8", errors="replace") as fh:
            for stage, cmd in zip(item["stages"], item["commands"]):
                fh.write(f"\n=== {item['subject']} :: {stage} :: "
                         f"{datetime.now():%H:%M:%S}\n")
                fh.write("$ " + " ".join(cmd) + "\n")
                fh.flush()
                rec["stage"] = stage
                _write(st_path, status)
                try:
                    code = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                           cwd=job["cwd"])
                except Exception as e:                      # noqa: BLE001
                    fh.write(f"[batch] could not start: {e}\n")
                    code = 127
                rec.setdefault("codes", {})[stage] = code
                if code != 0:
                    # a failed stage poisons the ones after it (no IK -> no SO),
                    # so stop this SUBJECT and carry on with the next
                    fh.write(f"[batch] {stage} exited {code} -- "
                             f"skipping the rest for {item['subject']}\n")
                    break
        rec["seconds"] = round(time.time() - t0, 1)
        rec["state"] = "failed" if any(c != 0 for c in rec.get("codes", {}).values()) \
            else "done"
        rec["stage"] = None
        bad += rec["state"] == "failed"
        _write(st_path, status)

    status["state"] = "finished"
    status["failed"] = bad
    status["ended"] = datetime.now().isoformat(timespec="seconds")
    _write(st_path, status)
    return 1 if bad else 0


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #
def _show_status(project: Path, job_id=None) -> int:
    root = project / "logs" / "batch"
    jobs = sorted((p for p in root.glob("*/status.json")), reverse=True)
    if not jobs:
        print(f"[run] no jobs under {root}")
        return 0
    if job_id:
        jobs = [p for p in jobs if p.parent.name == job_id] or jobs[:1]
    for st_path in (jobs if job_id else jobs[:5]):
        st = json.loads(st_path.read_text(encoding="utf-8"))
        print(f"\n{st_path.parent.name}  {st['state']}"
              f"  ({st.get('started', '?')} -> {st.get('ended', '...')})")
        for sub, rec in st["subjects"].items():
            mark = {"done": "ok", "failed": "FAILED",
                    "running": "running", "pending": "-"}.get(rec["state"], "?")
            extra = f" [{rec['stage']}]" if rec.get("stage") else ""
            secs = f"  {rec['seconds'] / 60:.1f} min" if rec.get("seconds") else ""
            print(f"   {sub:8} {mark:8}{extra}{secs}")
            if job_id and rec.get("codes"):
                for stage, code in rec["codes"].items():
                    print(f"       {stage:10} exit {code}")
            if job_id:
                print(f"       log: {rec['log']}")
    return 0


# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bioscout run",
        description="run stages for several subjects in the background")
    p.add_argument("subjects", nargs="*", metavar="ID",
                   help="subject ids, e.g. 009 010 011")
    p.add_argument("--session", default="pre", metavar="NAME")
    p.add_argument("--iteration", default="gpk", metavar="NAME")
    p.add_argument("--trial", default=None, metavar="A,B",
                   help="comma-separated trials (default: session.yaml's list)")
    p.add_argument("--stages", default=",".join(DEFAULT_STAGES), metavar="A,B",
                   help=f"default: {','.join(DEFAULT_STAGES)}")
    p.add_argument("--replace", action="store_true",
                   help="recompute outputs that already exist")
    p.add_argument("--project", default=".", metavar="DIR")
    p.add_argument("--status", nargs="?", const="", metavar="JOB_ID",
                   help="show recent jobs, or one job in detail")
    p.add_argument("--foreground", action="store_true",
                   help="run here instead of detaching (for debugging)")
    p.add_argument("--worker", metavar="JOB_JSON", help=argparse.SUPPRESS)
    return p


def main(argv=None) -> int:
    ns = build_parser().parse_args(argv)
    if ns.worker:
        return _run_worker(ns.worker)
    project = Path(ns.project).resolve()
    if ns.status is not None:
        return _show_status(project, ns.status or None)
    if not ns.subjects:
        print("[run] give at least one subject id, or --status")
        return 2

    stages = [s.strip() for s in ns.stages.split(",") if s.strip()]
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        print(f"[run] unknown stage(s): {', '.join(unknown)}\n"
              f"      known: {', '.join(STAGES)}")
        return 2

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jd = _job_dir(project, stamp)
    items, status = [], {"job": stamp, "state": "pending", "subjects": {}}
    for sub in ns.subjects:
        session = str(Path("simulations") / sub / ns.session)
        log = jd / f"{sub}.log"
        items.append({"subject": sub, "log": str(log), "stages": stages,
                      "commands": [_command(s, session, ns.iteration, ns.trial,
                                            ns.replace) for s in stages]})
        status["subjects"][sub] = {"state": "pending", "log": str(log),
                                   "stage": None}
    job = {"cwd": str(project), "items": items, "status": str(jd / "status.json")}
    _write(jd / "job.json", job)
    _write(jd / "status.json", status)

    try:
        from bioscout import __version__ as _v
    except Exception:                                        # noqa: BLE001
        _v = "unknown"
    print(f"bioscout {_v}  ·  job {stamp}")
    print(f"  {len(ns.subjects)} subject(s) x {len(stages)} stage(s): "
          f"{', '.join(stages)}")
    print(f"  iteration {ns.iteration}"
          f"{'  trials ' + ns.trial if ns.trial else ''}"
          f"{'  --replace' if ns.replace else ''}")
    for sub in ns.subjects:
        print(f"    {sub}  ->  {status['subjects'][sub]['log']}")

    if ns.foreground:
        return _run_worker(str(jd / "job.json"))

    cmd = [sys.executable, "-m", "bioscout.core.batch", "--worker",
           str(jd / "job.json")]
    kw = {"cwd": str(project), "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP
                               | getattr(subprocess, "DETACHED_PROCESS", 0x8))
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kw)                       # noqa: S603
    status["pid"] = proc.pid
    _write(jd / "status.json", status)
    print(f"\n  running in the background (pid {proc.pid}). The terminal is free.")
    print(f"  bioscout run --status           progress")
    print(f"  bioscout run --status {stamp}  detail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
