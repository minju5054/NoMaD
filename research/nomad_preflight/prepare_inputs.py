"""Extract exact JPEG bytes from the official GoStanford ZIP, without unpickling data."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    # First trajectory in the official archive; no output-driven scene selection.
    trajectory = "go_stanford/no3vcF_33_0"
    frames = {**{f"obs_{i}.jpg": 10 + i for i in range(4)}, "goal.jpg": 25,
              **{f"alternate_{i}.jpg": 14 + i for i in range(4)}}
    manifest = {"source_folder": "https://drive.google.com/drive/folders/1RYseCpbtHEFOsmSX2uqNY_kvSxwZLVP_",
                "file_id": "1BVGA46WbvOZFyuzkzV2n_yZqcQsdIJy7", "archive": str(args.archive.resolve()),
                "archive_bytes": args.archive.stat().st_size, "trajectory": trajectory,
                "selection": "First listed trajectory, observation indices 10..13, future goal 25, alternate observation indices 14..17",
                "time_semantics": "Ordered dataset frame indices only; no acquisition timestamps or native action times inferred",
                "frames": []}
    h = hashlib.sha256()
    with args.archive.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    manifest["archive_sha256"] = h.hexdigest()
    with zipfile.ZipFile(args.archive) as z:
        for target, frame in frames.items():
            member = f"{trajectory}/{frame}.jpg"
            data = z.read(member)
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                assert im.mode == "RGB", (member, im.mode)
                metadata = {"mode": im.mode, "size": list(im.size)}
            with (args.output / target).open("xb") as f:
                f.write(data)
            manifest["frames"].append({"file": target, "archive_member": member,
                                       "sha256": hashlib.sha256(data).hexdigest(), **metadata})
    with (args.output / "manifest.json").open("x") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
