"""Fetch only the exact official assets, preserving existing files and verifying SHA-256."""
import argparse
import hashlib
from pathlib import Path
import urllib.request

ASSETS = {
    "checkpoint": ("1YJhkkMJAYOiKNyCaelbS_alpUpAJsOUb", "checkpoints/nomad.pth", 76473631,
                   "70f79b8262527e20e56ced64a3e3d7ef91855bc9e7c3fa348d78edcb83c6a333"),
    "inputs": ("1BVGA46WbvOZFyuzkzV2n_yZqcQsdIJy7", "inputs/raw/go_stanford.zip", 781698396,
               "1fe1411945abd9cd0f335e845fe40d3477aac641aeb5669c961ec9debc4fb8a4"),
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("assets", choices=list(ASSETS), nargs="+")
    args = parser.parse_args()
    for key in args.assets:
        file_id, relative, size, expected_hash = ASSETS[key]
        destination = args.root / relative
        if destination.exists():
            if destination.stat().st_size != size or sha256(destination) != expected_hash:
                raise RuntimeError(f"Existing asset differs; refusing overwrite: {destination}")
            print(f"Verified existing {destination}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".partial")
        url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
        # Exclusive partial file: failed/partial downloads are retained for diagnosis.
        with partial.open("xb") as output, urllib.request.urlopen(url, timeout=120) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if partial.stat().st_size != size or sha256(partial) != expected_hash:
            raise RuntimeError(f"Official download differs (possibly access/quota HTML); retained {partial}")
        # Hard-link creation is exclusive, so a concurrent destination cannot be replaced.
        destination.hardlink_to(partial)
        partial.unlink()
        print(f"Downloaded and verified {destination}")


if __name__ == "__main__":
    main()
