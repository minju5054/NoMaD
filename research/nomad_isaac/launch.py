"""Launch existing Isaac 6 and NoMaD interpreters as separate local processes."""
import argparse
from datetime import datetime
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

from .common import ROOT, SCENARIO_PATH, read_scenario, sha256_file, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isaac-root", type=Path, default=Path("/home/gpuadmin/isaacsim"))
    parser.add_argument("--prepare-only", action="store_true", help="Render/frame gate only; no inference or movement")
    parser.add_argument("--scenario", type=Path, default=SCENARIO_PATH)
    parser.add_argument("--asynchronous", action="store_true", help="Paced OLD execution while GPU inference runs")
    parser.add_argument("--pure-pursuit", action="store_true", help="Phase 0-C frozen S0 chunk follower PILOT")
    parser.add_argument("--s0-delay-sweep", action="store_true", help="Frozen Phase 3 S0 RAW+PP delay sweep")
    parser.add_argument("--phase2-method", choices=["M0", "M3", "M5"])
    parser.add_argument("--diagnostic-condition", choices=["C1", "C2", "C3"])
    parser.add_argument("--phase2-distance-m", type=float, choices=[.6, .8, 1., 1.2])
    parser.add_argument("--s1-mode", action="store_true", help="Frozen Phase 1 S1 PP/Topomap/uniform-delay pilot")
    parser.add_argument("--s1-v2-mode", action="store_true", help="Frozen obstacle-free straight corridor pilot")
    parser.add_argument("--s1-distance-m", type=float, choices=[.8, 1., 1.2, 1.5])
    parser.add_argument("--seed-offset", type=int, default=0, help="Optional static S0 Topomap run seed offset")
    parser.add_argument("--run-id", help="Frozen Phase 0-D pair ID S0_01 ... S0_10")
    parser.add_argument("--oracle-safety-stop", action="store_true", help="Exact-geometry STOP after adaptive dynamic spawn")
    parser.add_argument("--early-obstacle-mode", choices=["raw", "graph"], help="Frozen early fixed-location experiment")
    parser.add_argument("--topomap", type=Path, help="Verified static Topomap manifest for the NoMaD worker")
    parser.add_argument("--render-topomap-reference", type=Path, help="Render saved reference poses only; requires --prepare-only")
    parser.add_argument("--controlled-delivery-delay", action="store_true", help="Single predeclared 0.5 s IPC result hold")
    parser.add_argument("--uniform-delivery-delay-s", type=float, choices=[0., .25, .5, .75],
                        help="Hold every accepted result after packet receive")
    args = parser.parse_args()
    if args.s0_delay_sweep:
        from nomad_phase3.config import validate_options
        validate_options(args)
    if args.diagnostic_condition and not args.phase2_method:
        raise ValueError("Diagnostic condition requires M0 Phase2 execution")
    if args.phase2_method:
        from nomad_phase2.config import validate_options
        validate_options(args)
    elif args.phase2_distance_m is not None:
        raise ValueError("Phase2 distance requires Phase2 method")
    if args.s1_v2_mode:
        from nomad_phase1.s1_v2 import validate_options
        validate_options(args)
    if args.s1_mode:
        from nomad_phase1.s1 import validate_options
        validate_options(args)
    elif args.s1_distance_m is not None:
        parser.error("--s1-distance-m requires --s1-mode")
    from .seed_offset import validate_seed_options
    validate_seed_options(args)
    if args.pure_pursuit:
        from nomad_phase0.chunk_execution import validate_mode
        validate_mode(args)
    if args.early_obstacle_mode:
        from .early_experiment import validate_early
        if not args.topomap:
            parser.error("Early experiment requires its fixed Topomap")
        validate_early(read_scenario(args.scenario), args.topomap, args.asynchronous, args.prepare_only,
                       args.controlled_delivery_delay, args.uniform_delivery_delay_s, args.oracle_safety_stop)
    if args.oracle_safety_stop and (not args.topomap or not args.asynchronous or args.prepare_only
            or args.controlled_delivery_delay or args.uniform_delivery_delay_s is not None
            or "placement" not in read_scenario(args.scenario).get("dynamic_obstacle", {})):
        parser.error("Oracle Safety Stop requires the frozen asynchronous Topomap + adaptive obstacle, zero-delay experiment")
    if args.topomap and not (args.s1_mode or args.s1_v2_mode or args.phase2_method or args.s0_delay_sweep) and (not args.asynchronous or args.prepare_only or args.controlled_delivery_delay or args.uniform_delivery_delay_s is not None):
        parser.error("Topomap navigation requires asynchronous execution without extra delay")
    if args.render_topomap_reference and (not args.prepare_only or args.topomap):
        parser.error("Reference rendering requires --prepare-only and no navigation Topomap")
    if args.render_topomap_reference:
        assert "dynamic_obstacle" not in read_scenario(args.scenario)
    if args.topomap and "dynamic_obstacle" in read_scenario(args.scenario) and not args.early_obstacle_mode and not args.s1_mode and not args.phase2_method:
        from .topomap import validate_dynamic_combination
        validate_dynamic_combination(read_scenario(args.scenario), args.topomap, args.asynchronous,
                                     args.prepare_only, args.controlled_delivery_delay, args.uniform_delivery_delay_s)
    if args.controlled_delivery_delay and (not args.asynchronous or args.prepare_only):
        parser.error("Controlled delivery delay requires asynchronous navigation")
    if args.uniform_delivery_delay_s is not None and (not args.asynchronous or args.prepare_only or args.controlled_delivery_delay):
        parser.error("Uniform delivery delay requires asynchronous navigation without single-trigger mode")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    isaac = args.isaac_root.resolve()
    version = (isaac / "VERSION").read_text().strip()
    if not version.startswith("6."):
        raise RuntimeError(f"Expected existing Isaac Sim 6, got {version}")
    scenario_path = args.scenario.resolve()
    sources = list(Path(__file__).parent.glob("*.py")) + [scenario_path, ROOT / "research/nomad_preflight/native.py"]
    if args.phase2_method:
        sources += list((ROOT/"research/nomad_phase2").glob("*.py"))+[ROOT/"research/nomad_phase2/protocol.json"]
        sources += [ROOT/"research/nomad_phase0"/n for n in ("graph_v4.py","graph_v4_protocol.json")]
    if args.s1_mode:
        sources += list((ROOT/"research/nomad_phase1").glob("*.py"))
        sources += [ROOT/"research/nomad_phase1/s1_protocol.json"]
        write_json(out/"s1_protocol.json", json.loads((ROOT/"research/nomad_phase1/s1_protocol.json").read_text()))
    if args.s1_v2_mode:
        sources += [ROOT/"research/nomad_phase1"/n for n in ("s1_v2.py", "s1_v2_protocol.json")]
        write_json(out/"s1_v2_protocol.json", json.loads((ROOT/"research/nomad_phase1/s1_v2_protocol.json").read_text()))
    if args.pure_pursuit:
        sources += [ROOT/"research/nomad_phase0"/name for name in
                    ("pure_pursuit.py", "chunk_execution.py", "chunk_pilot_protocol.json", "follower_protocol.json")]
    if args.seed_offset or args.run_id is not None:
        sources += [ROOT/"research/nomad_phase0/chunk_pilot_protocol.json"]
    if args.diagnostic_condition:
        sources += list((ROOT/"research/nomad_diagnostic").glob("*.py"))+[ROOT/"research/nomad_diagnostic/protocol.json"]
    if args.s0_delay_sweep:
        from nomad_phase3.config import HERE, protocol
        sources += list(HERE.glob("*.py"))+[HERE/"protocol.json"]
        write_json(out/"phase3_protocol.json", protocol())
    if args.run_id is not None and not args.phase2_method and not args.s0_delay_sweep:
        batch_protocol = ROOT/"research/nomad_phase0/s0_batch_protocol.json"
        sources += [batch_protocol]
        write_json(out/"batch_protocol.json", json.loads(batch_protocol.read_text()))
    if args.topomap or args.render_topomap_reference:
        sources += [Path(__file__).with_name("topomap_protocol.json")]
    if args.topomap and "dynamic_obstacle" in read_scenario(args.scenario):
        sources += [Path(__file__).with_name("topomap_sudden_protocol.json")]
    if args.oracle_safety_stop:
        sources += [Path(__file__).with_name("oracle_safety_stop_protocol.json")]
    if args.early_obstacle_mode:
        sources += [Path(__file__).with_name(name) for name in ("early_graph_protocol.json", "online_graph_factor_protocol.json")]
    if args.controlled_delivery_delay:
        sources += [Path(__file__).with_name("controlled_latency_protocol.json")]
    if args.uniform_delivery_delay_s is not None:
        sources += [Path(__file__).with_name("uniform_latency_protocol.json")]
    write_json(out / "provenance.json", {
        "time_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(), "isaac_root": str(isaac),
        "isaac_version": version, "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in sources},
        "prepare_only": args.prepare_only, "asynchronous": args.asynchronous,
        "oracle_safety_stop": args.oracle_safety_stop,
        "diagnostic_condition": args.diagnostic_condition, "phase2_method": args.phase2_method, "phase2_distance_m": args.phase2_distance_m,
        "pure_pursuit": args.pure_pursuit, "s0_delay_sweep": args.s0_delay_sweep,
        "s1_v2_mode": args.s1_v2_mode, "s1_mode": args.s1_mode, "s1_distance_m": args.s1_distance_m,
        "run_id": args.run_id, "seed_offset": args.seed_offset,
        "source_scenario_sha256": sha256_file(scenario_path),
        "early_obstacle_mode": args.early_obstacle_mode,
        "topomap_manifest": str(args.topomap.resolve()) if args.topomap else None,
        "topomap_manifest_sha256": sha256_file(args.topomap) if args.topomap else None,
        "render_topomap_reference": str(args.render_topomap_reference.resolve()) if args.render_topomap_reference else None,
        "controlled_delivery_delay": args.controlled_delivery_delay,
        "uniform_delivery_delay_s": args.uniform_delivery_delay_s, "launcher_python": sys.executable,
        "gpu": subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], text=True).strip()})
    worker = None
    simulator = None
    socket_path = out / "ipc.sock"
    with (out / "worker.log").open("x") as worker_log, (out / "simulator.log").open("x") as sim_log:
        try:
            # Spawn both from this clean parent, never from Isaac's library environment.
            worker_env = os.environ.copy()
            worker_env["PYTHONPATH"] = ":".join(str(ROOT / p) for p in ["research", "train", "external/diffusion_policy"])
            worker_env["PYTHONPYCACHEPREFIX"] = str(out / "worker_pycache")
            if not args.prepare_only:
                worker_command = [str(ROOT.parent / ".venv/bin/python"), "-u", "-m", "nomad_isaac.worker",
                    "--socket", str(socket_path), "--output", str(out / "model"),
                    "--checkpoint", str(ROOT.parent / "artifacts/checkpoints/nomad.pth")]
                if args.topomap:
                    worker_command += ["--topomap", str(args.topomap.resolve())]
                if args.diagnostic_condition:
                    worker_command += ["--diagnostic"]
                worker = subprocess.Popen(worker_command,
                    cwd=ROOT, env=worker_env, stdout=worker_log, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 90
                while not socket_path.exists():
                    if worker.poll() is not None:
                        raise RuntimeError("NoMaD worker startup failed; see worker.log")
                    if time.monotonic() >= deadline:
                        raise TimeoutError("NoMaD worker startup exceeded 90 seconds")
                    time.sleep(.1)
            env = os.environ.copy()
            # No .venv site-packages or torch libraries are injected into Isaac Sim.
            for key in ["PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME", "LD_LIBRARY_PATH", "LD_PRELOAD"]:
                env.pop(key, None)
            env["PYTHONPATH"] = str(ROOT / "research")
            for key, folder in [("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"),
                                ("CUDA_CACHE_PATH", "cuda_cache"), ("__GL_SHADER_DISK_CACHE_PATH", "gl_cache"),
                                ("PYTHONPYCACHEPREFIX", "isaac_pycache")]:
                env[key] = str(out / folder)
                Path(env[key]).mkdir()
            command = [str(isaac / "python.sh"), str(Path(__file__).with_name("simulator.py")),
                       "--output", str(out), "--scenario", str(scenario_path), "--portable-root", str(out / "portable")]
            command += ["--prepare-only"] if args.prepare_only else ["--socket", str(socket_path)]
            if args.asynchronous:
                command.append("--asynchronous")
            if args.pure_pursuit:
                command.append("--pure-pursuit")
            if args.s0_delay_sweep:
                command.append("--s0-delay-sweep")
            if args.phase2_method:
                command += ["--phase2-method", args.phase2_method]
                if args.diagnostic_condition:
                    command += ["--diagnostic-condition", args.diagnostic_condition]
                if args.phase2_distance_m is not None:
                    command += ["--phase2-distance-m",str(args.phase2_distance_m)]
            if args.s1_v2_mode:
                command.append("--s1-v2-mode")
            if args.s1_mode:
                command += ["--s1-mode", "--s1-distance-m", str(args.s1_distance_m)]
            if args.seed_offset:
                command += ["--seed-offset", str(args.seed_offset)]
            if args.run_id is not None:
                command += ["--run-id", args.run_id]
            if args.oracle_safety_stop:
                command.append("--oracle-safety-stop")
            if args.early_obstacle_mode:
                command += ["--early-obstacle-mode", args.early_obstacle_mode]
            if args.topomap:
                command += ["--topomap", str(args.topomap.resolve())]
            if args.render_topomap_reference:
                command += ["--render-topomap-reference", str(args.render_topomap_reference.resolve())]
            if args.controlled_delivery_delay:
                command.append("--controlled-delivery-delay")
            if args.uniform_delivery_delay_s is not None:
                command += ["--uniform-delivery-delay-s", str(args.uniform_delivery_delay_s)]
            simulator = subprocess.Popen(command, cwd=ROOT, env=env, stdout=sim_log, stderr=subprocess.STDOUT, start_new_session=True)
            print(f"Isaac PID {simulator.pid}; logs: {out}", flush=True)
            code = simulator.wait(timeout=read_scenario(scenario_path)["timeout_process_wall_s"])
            expected = "render_check.json" if args.prepare_only else "summary.json"
            if code != 0 or not (out / expected).exists() or (out / "FAILED.txt").exists():
                raise RuntimeError(f"Isaac adapter did not complete (exit {code}); see {out}")
            if args.render_topomap_reference and not (out / "topomap/manifest.json").exists():
                raise RuntimeError("Reference Topomap manifest missing")
            if worker is not None and worker.wait(timeout=15) != 0:
                raise RuntimeError("Worker failed after simulator; see worker.log")
            print(f"Completed: {out / expected}", flush=True)
        except Exception as exc:
            write_json(out / "launch_failure.json", {"type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            for process in [simulator, worker]:
                if process is not None and process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait()
            if socket_path.exists():
                socket_path.unlink()


if __name__ == "__main__":
    main()
