"""Only NumPy/stdlib: safe to import in either isolated Python runtime."""
import ast
import hashlib
import io
import json
import math
from pathlib import Path
import struct
from typing import Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = Path(__file__).with_name("scenario.json")


def read_scenario():
    return json.loads(SCENARIO_PATH.read_text())


def original_controller():
    path = ROOT / "deployment/src/pd_controller.py"
    nodes = [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)
             and n.name in ("clip_angle", "pd_controller")]
    assert len(nodes) == 2
    ns = {"np": np, "Tuple": Tuple, "EPS": 1e-8, "DT": 0.25, "MAX_V": 0.2, "MAX_W": 0.4}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    return ns["pd_controller"]


def controller_2d(waypoint):
    """Explicit 2D formula, numerically compared with the full original function."""
    dx, dy = np.asarray(waypoint)
    if abs(dx) < 1e-8:
        v = 0
        w = np.sign(dy) * np.pi / (2 * 0.25)
    else:
        v = dx / 0.25
        w = np.arctan(dy / dx) / 0.25
    return np.clip(v, 0, 0.2), np.clip(w, -0.4, 0.4)


def integrate_se2(pose, v, w, dt):
    """Exact unicycle integration over one constant-command interval; no clipping."""
    x, y, yaw = pose
    turn = w * dt
    # Stable sinc expression also handles exactly zero angular velocity.
    distance = v * dt * np.sinc(turn / (2 * np.pi))
    return np.array([x + distance * math.cos(yaw + turn / 2),
                     y + distance * math.sin(yaw + turn / 2),
                     (yaw + turn + np.pi) % (2 * np.pi) - np.pi])


def local_to_world(points, pose):
    c, s = np.cos(pose[2]), np.sin(pose[2])
    return np.asarray(points) @ np.array([[c, s], [-s, c]]) + pose[:2]


def send_packet(connection, metadata, **arrays):
    buffer = io.BytesIO()
    np.savez(buffer, metadata=np.frombuffer(json.dumps(metadata).encode(), dtype=np.uint8), **arrays)
    payload = buffer.getvalue()
    connection.sendall(struct.pack("!I", len(payload)) + payload)


def _read_exact(connection, length):
    parts = bytearray()
    while len(parts) < length:
        chunk = connection.recv(length - len(parts))
        if not chunk:
            raise EOFError("Local inference process disconnected")
        parts.extend(chunk)
    return bytes(parts)


def receive_packet(connection):
    size = struct.unpack("!I", _read_exact(connection, 4))[0]
    if not 0 < size <= 16 * 1024 * 1024:
        raise ValueError(f"Invalid packet size {size}")
    with np.load(io.BytesIO(_read_exact(connection, size)), allow_pickle=False) as packet:
        metadata = json.loads(packet["metadata"].tobytes())
        arrays = {k: packet[k].copy() for k in packet.files if k != "metadata"}
    return metadata, arrays


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
