"""Crop author-provided camera/goal insets from the official indoor demonstration."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    assert hashlib.sha256(args.video.read_bytes()).hexdigest() == "231b4ee180b9384d23d0245c0b8ea2a8842acb7702d7bd0910380b0a2d8ad94d"
    cap = cv2.VideoCapture(str(args.video))
    assert cap.isOpened()
    fps = cap.get(cv2.CAP_PROP_FPS)
    assert (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT), fps) == (1280., 720., 30.)
    obs_crop = (885, 417, 1244, 686)
    goal_crop = (885, 30, 1250, 303)
    frames = [(f"obs_{i}.png", 30 + i * 8, obs_crop) for i in range(4)]
    frames += [("goal.png", 60, goal_crop)]
    frames += [(f"alternate_{i}.png", 60 + i * 8, obs_crop) for i in range(4)]
    manifest = {"source": "https://general-navigation-models.github.io/nomad/static/videos/nomad_indoors.mp4",
                "video_sha256": hashlib.sha256(args.video.read_bytes()).hexdigest(),
                "video_bytes": args.video.stat().st_size, "decoder": f"opencv {cv2.__version__}",
                "video_fps": fps, "frames": [],
                "limitations": ["Published edited video, not raw sensor data", "Yellow predicted-trajectory overlays retained in observation inset", "Video presentation times are not sensor or predicted-action timestamps", "Execution-only auxiliary verification, no obstacle-avoidance claim"]}
    for name, index, box in frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, bgr = cap.read()
        assert ok
        image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).crop(box)
        path = args.output / name
        with path.open("xb") as f:
            image.save(f, format="PNG")
        manifest["frames"].append({"file": name, "video_frame": index, "presentation_seconds": index / fps,
                                   "crop_ltrb": box, "mode": image.mode, "size": image.size,
                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    cap.release()
    with (args.output / "manifest.json").open("x") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
