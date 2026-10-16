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
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    isaac = args.isaac_root.resolve()
    version = (isaac / "VERSION").read_text().strip()
    if not version.startswith("6."):
        raise RuntimeError(f"Expected existing Isaac Sim 6, got {version}")
    scenario_path = args.scenario.resolve()
    sources = list(Path(__file__).parent.glob("*.py")) + [scenario_path, ROOT / "research/nomad_preflight/native.py"]
    write_json(out / "provenance.json", {
        "time_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(), "isaac_root": str(isaac),
        "isaac_version": version, "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in sources},
        "prepare_only": args.prepare_only, "launcher_python": sys.executable,
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
                worker = subprocess.Popen([str(ROOT.parent / ".venv/bin/python"), "-u", "-m", "nomad_isaac.worker",
                    "--socket", str(socket_path), "--output", str(out / "model"),
                    "--checkpoint", str(ROOT.parent / "artifacts/checkpoints/nomad.pth")],
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
            simulator = subprocess.Popen(command, cwd=ROOT, env=env, stdout=sim_log, stderr=subprocess.STDOUT, start_new_session=True)
            print(f"Isaac PID {simulator.pid}; logs: {out}", flush=True)
            code = simulator.wait(timeout=read_scenario(scenario_path)["timeout_process_wall_s"])
            expected = "render_check.json" if args.prepare_only else "summary.json"
            if code != 0 or not (out / expected).exists() or (out / "FAILED.txt").exists():
                raise RuntimeError(f"Isaac adapter did not complete (exit {code}); see {out}")
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
