"""Fixed S0 paired runner. --dry-run does not start Isaac, GPU inference or a child job."""
import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import shlex
import subprocess
import time
import traceback
from types import SimpleNamespace

from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.seed_offset import request_seed, validate_seed_options
from nomad_isaac.topomap_report import validate_map
from .s0_batch_metrics import PROTOCOL_PATH, SCOPE, extract_run, protocol, save_aggregate, write_csv


def git_state():
    return {"git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)}


def build_plan(run_root):
    p = protocol()
    scenario, topomap = ROOT/p["scenario"], ROOT.parent/p["topomap"]
    state = git_state()
    manifest, map_check = validate_map(topomap)
    assert manifest["node_count"] == p["topomap_nodes"] == 14
    fixed_files = [scenario, topomap, ROOT/"research/nomad_phase0/pure_pursuit.py",
                   ROOT/"research/nomad_phase0/chunk_pilot_protocol.json", ROOT/"deployment/src/pd_controller.py",
                   ROOT.parent/"artifacts/checkpoints/nomad.pth"]
    jobs = []
    for i, offset in enumerate(p["offsets"], 1):
        identifier = f"S0_{i:02d}"
        for condition in p["conditions_in_order"]:
            options = SimpleNamespace(seed_offset=offset, run_id=identifier, scenario=scenario,
                topomap=topomap, asynchronous=True, prepare_only=False, oracle_safety_stop=False,
                early_obstacle_mode=None, controlled_delivery_delay=False, uniform_delivery_delay_s=None,
                render_topomap_reference=None)
            validate_seed_options(options)
            output = run_root/identifier/condition
            command = ["env", "-u", "LD_LIBRARY_PATH", "-u", "LD_PRELOAD", "-u", "PYTHONHOME",
                       "-u", "VIRTUAL_ENV", "bash", str(ROOT/"research/python.sh"), "-m", "nomad_isaac.launch",
                       "--asynchronous", "--scenario", str(scenario), "--topomap", str(topomap),
                       "--seed-offset", str(offset), "--run-id", identifier, "--output", str(output)]
            if condition == "PP":
                command.append("--pure-pursuit")
            jobs.append({"scope": SCOPE, "run_id": identifier, "condition": condition, "seed_offset": offset,
                         "output": str(output), "argv": command, "shell_command": shlex.join(command),
                         "request_0_seed": request_seed({"seed": 101, "seed_offset": offset}, 0),
                         "request_0_ddpm_seed": request_seed({"seed": 101, "seed_offset": offset}, 0)+1})
    assert len(jobs) == 20 and len({j["output"] for j in jobs}) == 20
    return {"scope": SCOPE, "label": "PLAN_ONLY_NOT_RUN", **state, "run_root": str(run_root),
            "protocol": p, "protocol_sha256": sha256_file(PROTOCOL_PATH),
            "source_scenario_sha256": sha256_file(scenario), "topomap_manifest_sha256": sha256_file(topomap),
            "fixed_input_sha256": {str(path): sha256_file(path) for path in fixed_files},
            "scenario_config": json.loads(scenario.read_text()),
            "pp_settings": json.loads((ROOT/"research/nomad_phase0/chunk_pilot_protocol.json").read_text())["follower"],
            "map_preflight": map_check, "jobs": jobs}


def save_plan(out, plan):
    write_json(out/"plan.json", plan)
    write_csv(out/"seed_commands.csv", plan["jobs"])


@contextmanager
def exclusive_batch():
    """All invocations of this S0 runner share one lock, even with different roots."""
    path = ROOT.parent/"artifacts/isaac6/.phase0d_s0_batch.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another S0 batch is active; no navigation launched") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def launch_one(job, log_path):
    with log_path.open("x") as log:
        # Blocking subprocess.run is intentional: the next GPU job cannot start early.
        return subprocess.run(job["argv"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False).returncode


def execute_jobs(plan, root):
    """Exactly one launch attempt per planned job, including failed attempts."""
    (root/"launcher_logs").mkdir()
    (root/"metrics").mkdir()
    records = []
    with (root/"execution.jsonl").open("x") as journal:
        def record_event(event):
            journal.write(json.dumps({"scope": SCOPE, "monotonic_ns": time.monotonic_ns(), **event})+"\n")
            journal.flush()
        for job in plan["jobs"]:
            key = f"{job['run_id']}_{job['condition']}"
            record_event({"event": "START", "run_id": job["run_id"], "condition": job["condition"],
                          "seed_offset": job["seed_offset"], "argv": job["argv"]})
            exit_code = None
            stage = "input_validation"
            try:
                state = git_state()
                if state["git_status"] or state["git_sha"] != plan["git_sha"]:
                    raise RuntimeError("Checkout changed since batch plan; no child launched")
                if any(sha256_file(Path(path)) != digest for path, digest in plan["fixed_input_sha256"].items()):
                    raise RuntimeError("Frozen input changed since batch plan; no child launched")
                if Path(job["output"]).exists():
                    raise FileExistsError(f"Refusing existing output: {job['output']}")
                stage = "launcher"
                exit_code = launch_one(job, root/"launcher_logs"/f"{key}.log")
                if exit_code != 0:
                    raise RuntimeError(f"Launcher exit code {exit_code}; see launcher log")
                stage = "metric_extraction"
                metric = extract_run(Path(job["output"]), job["condition"], job["run_id"], job["seed_offset"])
            except Exception as exc:
                metric = {"scope": SCOPE, "run_id": job["run_id"], "condition": job["condition"],
                          "seed_offset": job["seed_offset"], "source_run": job["output"],
                          "classification": "TECHNICAL_FAILURE", "technical_failure": True,
                          "success": False, "safety_failure": None, "timeout": None, "goal_entry": None,
                          "goal_time_s": None, "execution_git_sha": plan["git_sha"],
                          "scenario_sha256": plan["source_scenario_sha256"],
                          "topomap_sha256": plan["topomap_manifest_sha256"], "runtime_config_sha256": None,
                          "failure_stage": stage, "error_type": type(exc).__name__, "error": str(exc),
                          "traceback": traceback.format_exc()}
            except BaseException as exc:
                record_event({"event": "INTERRUPTED", "run_id": job["run_id"], "condition": job["condition"],
                              "error_type": type(exc).__name__, "retry": False})
                raise
            metric["launcher_exit_code"] = exit_code
            write_json(root/"metrics"/f"{key}.json", metric)
            records.append(metric)
            record_event({"event": "END", "run_id": job["run_id"], "condition": job["condition"],
                          "classification": metric["classification"], "exit_code": exit_code, "retry": False})
    save_aggregate(root/"aggregate", records)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true", help="Future authorized 20-run batch; NOT part of Phase 0-D preflight")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="New dry-run report directory only")
    parser.add_argument("--delay-sweep", action="store_true", help="Phase 3 S0 PP only, frozen 20-run delay protocol")
    args = parser.parse_args()
    if args.dry_run != (args.output is not None):
        parser.error("--dry-run requires --output; --execute stores reports in --run-root")
    root = args.run_root.resolve()
    if root.exists():
        raise FileExistsError(f"Batch root already exists; no retry/resume or overwrite: {root}")
    if args.delay_sweep:
        from nomad_phase3.batch import run
        return run(args, root)
    plan = build_plan(root)
    if args.dry_run:
        out = args.output.resolve()
        if out == root or root in out.parents:
            parser.error("Dry-run reports must be outside the future execution root")
        out.mkdir(parents=True, exist_ok=False)
        save_plan(out, plan)
        print(json.dumps({"status": "DRY_RUN_ONLY", "planned_jobs": len(plan["jobs"]),
                          "navigation_started": 0, "out": str(out)}))
        return
    if plan["git_status"]:
        raise RuntimeError("Actual batch execution requires a clean committed checkout")
    with exclusive_batch():
        root.mkdir(parents=True, exist_ok=False)
        plan["label"] = "S0_BATCH_EXECUTION_PLAN"
        save_plan(root, plan)
        records = execute_jobs(plan, root)
    print(json.dumps({"scope": SCOPE, "attempts": len(records), "aggregate": str(root/"aggregate")}))


if __name__ == "__main__":
    main()
