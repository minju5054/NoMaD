"""Short AF_UNIX transport paths without changing experiment output paths."""
import hashlib
import os
from pathlib import Path


SOCKET_PATH_LIMIT = 100  # Strictly below Linux's 108-byte sockaddr_un field.


def validate_socket_path(path):
    size = len(os.fsencode(path))
    if size >= SOCKET_PATH_LIMIT:
        raise ValueError(f'AF_UNIX socket path is {size} bytes; must be < {SOCKET_PATH_LIMIT}: {path}')
    return size


def socket_path_for_run(output):
    output = Path(output).resolve()
    path = output / 'ipc.sock'
    if len(os.fsencode(path)) >= SOCKET_PATH_LIMIT:
        digest = hashlib.sha1(os.fsencode(output)).hexdigest()[:12]
        path = Path('/tmp') / f'nomad-{digest}.sock'
    validate_socket_path(path)
    return path
