"""Launch existing Isaac 6 and NoMaD interpreters as separate local processes."""
import argparse
from datetime import datetime
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
    parser.add_argument("--oracle-safety-stop", action="store_true", help="Exact-geometry STOP after adaptive dynamic spawn")
    parser.add_argument("--topomap", type=Path, help="Verified static Topomap manifest for the NoMaD worker")
    parser.add_argument("--render-topomap-reference", type=Path, help="Render saved reference poses only; requires --prepare-only")
    parser.add_argument("--controlled-delivery-delay", action="store_true", help="Single predeclared 0.5 s IPC result hold")
    parser.add_argument("--uniform-delivery-delay-s", type=float, choices=[0., .25, .5, .75],
                        help="Hold every accepted result after packet receive")
    args = parser.parse_args()
    if args.oracle_safety_stop and (not args.topomap or not args.asynchronous or args.prepare_only
            or args.controlled_delivery_delay or args.uniform_delivery_delay_s is not None
            or "placement" not in read_scenario(args.scenario).get("dynamic_obstacle", {})):
        parser.error("Oracle Safety Stop requires the frozen asynchronous Topomap + adaptive obstacle, zero-delay experiment")
    if args.topomap and (not args.asynchronous or args.prepare_only or args.controlled_delivery_delay or args.uniform_delivery_delay_s is not None):
        parser.error("Topomap navigation requires asynchronous execution without extra delay")
    if args.render_topomap_reference and (not args.prepare_only or args.topomap):
        parser.error("Reference rendering requires --prepare-only and no navigation Topomap")
    if args.render_topomap_reference:
        assert "dynamic_obstacle" not in read_scenario(args.scenario)
    if args.topomap and "dynamic_obstacle" in read_scenario(args.scenario):
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
    if args.topomap or args.render_topomap_reference:
        sources += [Path(__file__).with_name("topomap_protocol.json")]
    if args.topomap and "dynamic_obstacle" in read_scenario(args.scenario):
        sources += [Path(__file__).with_name("topomap_sudden_protocol.json")]
    if args.oracle_safety_stop:
        sources += [Path(__file__).with_name("oracle_safety_stop_protocol.json")]
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
            if args.oracle_safety_stop:
                command.append("--oracle-safety-stop")
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
