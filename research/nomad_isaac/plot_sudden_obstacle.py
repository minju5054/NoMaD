"""One recorded OLD/FRESH comparison with before/after RGB; no simulation."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .clearance import obstacle_bounds, single_obstacle_config
from .common import local_to_world, sha256_file, write_json


def plot(audit, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Rectangle

    report = json.loads((audit/"summary.json").read_text())
    assert report["fresh_applied"] and report["geometry"]["entry"]["valid"]
    run = Path(report["source_run"])
    hashes = {str(audit/"summary.json"): sha256_file(audit/"summary.json")}
    for name, digest in json.loads((audit/"input_hashes.json").read_text()).items():
        assert sha256_file(run/name) == digest
        hashes[str(run/name)] = digest
    config = json.loads((run/"scenario.json").read_text())
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True)
    poses = np.column_stack([trace[k] for k in ("x_m", "y_m", "yaw_rad")])
    times = trace["simulation_time_s"]
    boundary = np.array(report["boundary_pose"])
    switch = round(report["timing"]["switch_sim_s"]*config["integration_hz"])
    np.testing.assert_allclose(boundary, poses[switch], atol=1e-12, rtol=0)
    worlds = {}
    for kind in ("old", "fresh"):
        with np.load(run/f"model/derived/{report[kind+'_id']:04d}.npz") as z:
            worlds[kind] = local_to_world(z["metric"][0], report[kind+"_observation_pose"])
        np.testing.assert_allclose(worlds[kind], report[kind+"_world_xy_m"], atol=1e-12, rtol=0)
    entry = np.array(report["geometry"]["entry"]["chosen"]["xy_m"])
    visible_id = report["timing"]["first_visible_observation_id"]
    evidence = {e["observation_id"]: e for e in report["rgb_visibility_evidence"]}
    assert evidence[visible_id-1]["active"] is False and evidence[visible_id]["active"] is True

    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none",
                         "svg.hashsalt": "nomad-sudden-obstacle", "path.simplify": False})
    old_color, fresh_color, dynamic_color = "#b76804", "#2167ae", "#ad239f"
    fig = plt.figure(figsize=(15.6, 8.0))
    grid = fig.add_gridspec(2, 3, left=.055, right=.98, top=.82, bottom=.23,
                           width_ratios=[1, 1.38, .96], wspace=.24, hspace=.35)
    overview, detail = fig.add_subplot(grid[:, 0]), fig.add_subplot(grid[:, 1])
    rgb_axes = [fig.add_subplot(grid[i, 2]) for i in range(2)]

    for ax in (overview, detail):
        for box in [*config["obstacles"], config["dynamic_obstacle"]]:
            lower, upper = obstacle_bounds(single_obstacle_config(config, box))
            dynamic = box["id"] == "DynamicObstacle"
            ax.add_patch(Rectangle(lower, *(upper-lower), fc=dynamic_color if dynamic else "#a9c99c",
                                   ec=dynamic_color if dynamic else "#548543", alpha=.6, zorder=1))
        for kind, color in (("old", old_color), ("fresh", fresh_color)):
            points = worlds[kind]
            ax.plot(*points.T, "o-", ms=3, lw=2, c=color, zorder=3)
            ax.scatter(*points[2], s=50, marker="s", c=color, zorder=4)
            anchor = report[kind+"_observation_pose"]
            ax.scatter(*anchor[:2], s=55, facecolors="white", edgecolors=color, lw=1.6, zorder=7)
        for key, color in (("pre_fresh_execution", "#282c32"), ("fresh_execution", "#008c7a")):
            segment = report[key]
            selected = (times >= segment["start_sim_s"]-1e-9) & (times <= segment["end_sim_s"]+1e-9)
            ax.plot(*poses[selected, :2].T, color=color, lw=3.3, zorder=5)
        ax.plot([boundary[0], entry[0]], [boundary[1], entry[1]], "--", c="#ae3474", lw=2, zorder=6)
        ax.add_patch(Circle(boundary[:2], config["agent_radius_m"], fill=False, ec="#50545a", lw=1, zorder=2))
        ax.scatter(*boundary[:2], marker="D", s=38, c="#282c32", zorder=8)
        ax.scatter(*entry, marker="x", s=60, c="#ae3474", lw=2, zorder=8)
        ax.scatter(*report["spawn"]["pose"][:2], marker="^", s=35, c="#666666", zorder=7)
        ax.grid(alpha=.15); ax.set_aspect("equal")
        ax.set_xlabel("World X (m)"); ax.set_ylabel("World Y (m)")
        ax.spines[["right", "top"]].set_visible(False)

    overview.set(xlim=(1.15, 3.5), ylim=(-1.6, 1.6))
    for y in (-1.5, 1.5): overview.axhline(y, color="#65717c", lw=1.3)
    overview.text(1.5, 0, "Static 1", ha="center", va="center", fontsize=9)
    overview.text(3, .75, "Static 2", ha="center", va="center", fontsize=9)
    overview.annotate("New obstacle", (2.45, -.18), (2.45, -.9), ha="center", fontsize=9,
                      color=dynamic_color, arrowprops={"arrowstyle": "->", "color": dynamic_color})
    overview.add_patch(Rectangle((1.84, -.59), .88, .82, fill=False, ec="#8995a0", ls=":", lw=1.4))
    overview.set_title("A  |  Handoff location", loc="left", fontsize=11, pad=12)
    detail.set(xlim=(1.84, 2.72), ylim=(-.59, .23))
    detail.set_title("B  |  OLD 49 / FRESH 50\nEach anchored at its own observation pose", loc="left", fontsize=11, pad=12)
    annotations = [
        ("OLD observation", report["old_observation_pose"][:2], (1.88, .17), old_color),
        ("FRESH observation", report["fresh_observation_pose"][:2], (2.12, .10), fresh_color),
        ("Spawn pose", report["spawn"]["pose"][:2], (1.845, .115), "#666666"),
        ("B: switch", boundary[:2], (1.85, -.13), "#282c32"),
        ("Entry", entry, (2.11, -.075), "#ae3474"),
    ]
    for text, point, target, color in annotations:
        detail.annotate(text, point, target, color=color, fontsize=8.5,
                        arrowprops={"arrowstyle": "-", "lw": .7, "color": color}, zorder=9)
    detail.text(2.45, -.18, "Dynamic\n0.35 x 0.35 m", ha="center", va="center", color="#571352", fontsize=9)
    detail.text(2.43, -.43, "B to entry: 3.45 cm\nConnector clearance: 18.83 cm\nOffline connector; not PD execution",
                ha="center", fontsize=8.5, linespacing=1.6, color="#535b64")
    for ax, oid, label in zip(rgb_axes, (visible_id-1, visible_id), ("C  |  Before spawn", "D  |  First visible / FRESH input")):
        e = evidence[oid]
        ax.imshow(Image.open(run/e["rgb_file"]))
        ax.set_title(f"{label}\nRGB {oid}, t_sim = {e['simulation_time_s']:.2f} s", loc="left", fontsize=10, pad=8)
        ax.axis("off")

    fig.suptitle("Sudden obstacle pilot | Both OLD and FRESH were safe", fontsize=18, weight="bold", y=.97)
    fig.text(.5, .916, "Spawn 13.472 s  |  First visible RGB 13.500 s  |  Actual switch 13.667 s  |  NO_QUALIFIED_CANDIDATE",
             ha="center", fontsize=11, color="#48525d")
    handles = [Line2D([], [], c=old_color, marker="o", lw=2, label="OLD 49 (8 points)"),
               Line2D([], [], c=fresh_color, marker="o", lw=2, label="FRESH 50 (8 points)"),
               Line2D([], [], c="#555555", marker="s", ls="none", label="Selected index 2"),
               Line2D([], [], c="#282c32", lw=3, label="Actual OLD: spawn to switch"),
               Line2D([], [], c="#008c7a", lw=3, label="Actual FRESH: to next switch"),
               Line2D([], [], c="#ae3474", ls="--", lw=2, label="Offline boundary-entry connector")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, .105), ncol=3, frameon=False, fontsize=9)
    fig.text(.5, .055, "Paths are unsmoothed sample 0; square markers select index 2. Circle at B is the 9 cm footprint. Equal XY scales within each geometry panel.",
             ha="center", fontsize=8.5, color="#535b64")
    fig.text(.5, .027, "Visibility recovered from saved RGB and worker history hashes. Recorded instance masks failed (all zero); no rerun or model change.",
             ha="center", fontsize=8.5, color="#8b374c")
    fig.savefig(output/"sudden_obstacle_comparison.png", dpi=180, facecolor="white")
    svg = output/"sudden_obstacle_comparison.svg"
    fig.savefig(svg, metadata={"Date": None}, facecolor="white")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)
    assert all(sha256_file(Path(p)) == h for p, h in hashes.items())
    write_json(output/"manifest.json", {"source_run": str(run), "source_audit": str(audit),
        "old_id": report["old_id"], "fresh_id": report["fresh_id"], "rgb_observation_ids": [visible_id-1, visible_id],
        "input_count": len(hashes), "inputs_preserved": True,
        "checks": "All audit input hashes; original metric-to-world coordinates; actual switch pose",
        "source_sha256": sha256_file(Path(__file__)), "new_navigation_runs": 0, "new_inference_calls": 0,
        "output_sha256": {p.name: sha256_file(p) for p in sorted(output.iterdir())}})
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.audit.resolve(), args.output.resolve())
