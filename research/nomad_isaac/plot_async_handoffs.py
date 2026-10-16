"""Plot saved obstacle-region handoffs; never run inference or simulation."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .common import ROOT, local_to_world, sha256_file, write_json
from .clearance import configured_obstacles, obstacle_bounds, single_obstacle_config


def plot(run, audit, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Patch, Rectangle

    # Preserve both the input run and the already completed audit.
    recorded = json.loads((audit / "input_hashes.json").read_text())["sha256"]
    assert all(sha256_file(run / name) == digest for name, digest in recorded.items())
    sources = [audit / name for name in ("pair_details.json", "pairs.csv", "summary.json")]
    sources += [run / name for name in ("scenario.json", "agent_trajectory.csv")]
    before = {str(p): sha256_file(p) for p in sources}
    config = json.loads((run / "scenario.json").read_text())
    details = {d["fresh_id"]: d for d in json.loads((audit / "pair_details.json").read_text())}
    with (audit / "pairs.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    with (run / "agent_trajectory.csv").open() as stream:
        trace = list(csv.DictReader(stream))
    times = np.array([float(r["simulation_time_s"]) for r in trace])
    poses = np.array([[float(r[k]) for k in ("x_m", "y_m", "yaw_rad")] for r in trace])

    # Retrospective illustration only: these choices do not change correspondence,
    # entry selection, classification, or the audit's NO_QUALIFIED_CANDIDATE result.
    choices = [
        (18, 27, "progress_spatial_rmse_m", max, "Obstacle 1 approach", (.55, 1.75, .12, .77)),
        (28, 40, "progress_spatial_rmse_m", max, "Obstacle 1 passage", (1.0, 2.2, .12, .77)),
        (52, 62, "progress_spatial_rmse_m", max, "Obstacle 2 approach", (2.0, 3.2, -.48, .17)),
        (63, 75, "applied_interval_clearance_m", min, "Obstacle 2 passage", (2.4, 3.6, -.48, .17)),
    ]
    selected = []
    for lo, hi, metric, extreme, title, limits in choices:
        region = [r for r in rows if lo <= int(r["fresh_id"]) <= hi]
        if metric == "progress_spatial_rmse_m":
            region = [r for r in region if r["correspondence_valid"] == "True"]
        r = extreme(region, key=lambda r: float(r[metric]))
        d = details[int(r["fresh_id"])]
        for prefix, ident in (("old", d["old_id"]), ("fresh", d["fresh_id"])):
            with np.load(run / f"model/derived/{ident:04d}.npz", allow_pickle=False) as data:
                world = local_to_world(data["metric"][0], d[prefix + "_observation_pose"])
            np.testing.assert_allclose(world, d[prefix + "_world_xy_m"], atol=1e-12, rtol=0)
        start = round(float(r["t_switch_sim_s"]) * config["integration_hz"])
        end = round(float(r["applied_interval_end_sim_s"]) * config["integration_hz"])
        np.testing.assert_allclose(poses[start], d["boundary_pose"], atol=1e-12, rtol=0)
        np.testing.assert_allclose(times[[start, end]],
            [float(r["t_switch_sim_s"]), float(r["applied_interval_end_sim_s"])], atol=1e-12, rtol=0)
        selected.append((r, d, title, limits, start, end, metric, lo, hi, extreme.__name__))

    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "svg.fonttype": "none", "svg.hashsalt": "nomad-saved-handoffs"})
    old, fresh, actual, connector = "#ce7612", "#2165d6", "#087f7f", "#a02aa4"
    fig = plt.figure(figsize=(14.5, 13.5), facecolor="white")
    grid = fig.add_gridspec(3, 2, height_ratios=[.9, 1, 1], left=.065, right=.98,
                           top=.91, bottom=.12, wspace=.19, hspace=.92)
    overview = fig.add_subplot(grid[0, 0])
    key = fig.add_subplot(grid[0, 1]); key.axis("off")
    axes = [fig.add_subplot(grid[i, j]) for i in (1, 2) for j in (0, 1)]

    def obstacles(ax):
        for box in configured_obstacles(config):
            low, high = obstacle_bounds(single_obstacle_config(config, box))
            ax.add_patch(Rectangle(low, *(high-low), facecolor="#c5e6bf",
                                   edgecolor="#468048", lw=1.2, zorder=1))

    def style(ax):
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("World x (m)"); ax.set_ylabel("World y (m)")
        ax.grid(alpha=.17, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)

    obstacles(overview)
    overview.plot(*poses[:, :2].T, color="#70777d", lw=2)
    overview.scatter(*config["start_pose"][:2], c="black", marker="o", s=25)
    overview.text(-.08, -.19, "Start", fontsize=9)
    overview.add_patch(Circle(config["goal_pose"][:2], config["goal_tolerance_m"],
                             color="#087f7f", alpha=.10))
    overview.scatter(*config["goal_pose"][:2], c=actual, marker="*", s=100)
    overview.text(4.33, -.43, "Goal", fontsize=9)
    overview.axhline(config["corridor"]["half_width"], color="#5d6269", lw=2)
    overview.text(1.5, -.03, "1", ha="center", weight="bold")
    overview.text(3., .85, "2", ha="center", weight="bold")
    for label, (_, d, _, _, _, _, _, _, _, _) in zip("ABCD", selected):
        b = d["boundary_pose"]
        overview.scatter(*b[:2], s=35, c=fresh, zorder=4)
        overview.annotate(label, b[:2], xytext=(0, 13 if label in "AB" else -19),
                          textcoords="offset points", ha="center", weight="bold", color=fresh)
    overview.set(xlim=(-.2, 4.95), ylim=(-.57, 1.63))
    overview.set_title("Recorded route and four inspected switches", loc="left", fontsize=12, pad=9)
    style(overview)

    handles = [
        Line2D([], [], color=old, marker="o", ms=4, label="OLD: native 8-point sample 0"),
        Line2D([], [], color=fresh, marker="o", ms=4, label="FRESH: native 8-point sample 0"),
        Line2D([], [], color="#333333", marker="*", ls="none", ms=11, label="Star: selected waypoint index 2"),
        Line2D([], [], color="#555555", marker="s", mfc="white", ls="none", label="Square + arrow: observation pose / yaw"),
        Line2D([], [], color="black", marker="x", ls="none", ms=7, label="B: switch pose; circle: 9 cm footprint"),
        Line2D([], [], color=connector, marker="D", mfc="white", ls="--", ms=5, label="Entry + B connector (offline, unexecuted)"),
        Line2D([], [], color=actual, lw=4, label="Executed from this switch to the next"),
        Line2D([], [], color="#b6babd", lw=1.5, ls=":", label="Full recorded center path (context)"),
        Line2D([], [], color="#ce2635", lw=2.5, label="Unsafe FRESH tail / predicted footprint"),
        Patch(facecolor="#c5e6bf", edgecolor="#468048", label="Static obstacle (green)"),
    ]
    key.legend(handles=handles, loc="upper left", frameon=False, fontsize=9.1,
               borderaxespad=0, labelspacing=.48, handlelength=2.4)

    manifests = []
    for ax, label, (r, d, title, limits, start, end, metric, lo, hi, extremum) in zip(axes, "ABCD", selected):
        obstacles(ax)
        ax.plot(*poses[:, :2].T, color="#b6babd", lw=1.4, ls=":", zorder=2)
        ax.plot(*poses[start:end+1, :2].T, color="white", lw=7, zorder=5)
        ax.plot(*poses[start:end+1, :2].T, color=actual, lw=4.5, zorder=6)
        for prefix, color in (("old", old), ("fresh", fresh)):
            p = np.array(d[prefix + "_world_xy_m"])
            obs = d[prefix + "_observation_pose"]
            ax.plot(*p.T, "o-", color=color, lw=1.8, ms=4, zorder=4)
            ax.scatter(*p[2], marker="*", s=140, color=color, edgecolor="white", lw=.6, zorder=7)
            ax.scatter(*obs[:2], marker="s", s=38, facecolor="white", edgecolor=color, lw=1.5, zorder=8)
            ax.annotate("", xy=np.array(obs[:2])+.065*np.array([np.cos(obs[2]), np.sin(obs[2])]),
                        xytext=obs[:2], arrowprops={"arrowstyle": "->", "color": color, "lw": 1.1}, zorder=8)
        b = np.array(d["boundary_pose"])
        entry = np.array(d["entry"]["chosen"]["xy_m"])
        ax.add_patch(Circle(b[:2], config["agent_radius_m"], fill=False, ec="#333333", lw=1, ls="--", zorder=3))
        ax.plot(*np.vstack([b[:2], entry]).T, color=connector, ls="--", lw=2, zorder=9)
        ax.scatter(*entry, marker="D", s=40, facecolor="white", edgecolor=connector, lw=1.5, zorder=10)
        ax.scatter(*b[:2], marker="x", s=50, color="black", lw=1.8, zorder=11)
        ax.annotate("", xy=b[:2]+.065*np.array([np.cos(b[2]), np.sin(b[2])]),
                    xytext=b[:2], arrowprops={"arrowstyle": "->", "color": "black", "lw": 1}, zorder=11)
        ax.annotate("B", b[:2], xytext=(-12, -20), textcoords="offset points", fontsize=10, weight="bold")
        if d["fresh_id"] == 29:
            p = np.array(d["fresh_world_xy_m"])
            ax.plot(*p[6:8].T, color="#ce2635", lw=2.8, zorder=5)
            ax.add_patch(Circle(p[-1], config["agent_radius_m"], fill=False, ec="#ce2635", lw=1.2, zorder=5))
            ax.annotate("Predicted tail overlap\n(actual execution stayed safe)", p[-1], xytext=(1.73, .44),
                        fontsize=8.7, color="#b51c2a", arrowprops={"arrowstyle": "-", "color": "#b51c2a"})
        ax.set(xlim=limits[:2], ylim=limits[2:])
        style(ax)
        ax.set_title(f"{label}   {title}  |  OLD {d['old_id']} → FRESH {d['fresh_id']}\n"
                     f"Switch {times[start]:.2f} s  ·  position RMSE {100*float(r['progress_spatial_rmse_m']):.2f} cm"
                     f"  ·  tangent RMS {float(r['progress_heading_rms_deg']):.2f}°",
                     loc="left", fontsize=10.5, pad=12, linespacing=1.7)
        caption = (f"Min clearance: FRESH full {100*float(r['fresh_full_clearance_m']):.2f} cm; "
                   f"executed {100*float(r['applied_interval_clearance_m']):.2f} cm\n"
                   f"{d['class']}  ·  B→entry {100*d['entry']['chosen']['distance_m']:.2f} cm")
        ax.text(0, -.28, caption, transform=ax.transAxes, va="top", fontsize=9.1,
                color="#b51c2a" if d["class"] == "UNSAFE_FRESH" else "#39424a", linespacing=1.6)
        manifests.append({"panel": label, "old_id": d["old_id"], "fresh_id": d["fresh_id"],
            "class": d["class"], "region_fresh_ids": [lo, hi], "selection_metric": metric,
            "selection_extremum": extremum, "switch_sim_s": times[start],
            "executed_interval_end_sim_s": times[end], "metrics": {k: float(r[k]) for k in
                ("progress_spatial_rmse_m", "progress_heading_rms_deg", "fresh_full_clearance_m",
                 "fresh_prefix_clearance_m", "connector_clearance_m", "applied_interval_clearance_m")}})
    fig.suptitle("OLD / FRESH near the two obstacles", x=.065, ha="left", y=.98, fontsize=20, weight="bold")
    fig.text(.065, .941, "Saved asynchronous run: async_wide_wall_01  |  obstacle 2: 0.5 × 1.5 × 1.0 m  |  no new run or inference", fontsize=11, color="#4c5660")
    fig.text(.065, .013, "World XY; each prediction stays anchored at its own observation pose. No point-index correspondence is implied.\n"
             "Retrospective illustrations, not qualified Graph candidates. Required clearance: 2 cm. Zoom panels crop obstacle geometry; full geometry is above.",
             fontsize=9.2, color="#4c5660", linespacing=1.6)
    for extension in ("png", "svg"):
        fig.savefig(output / f"obstacle_handoffs.{extension}", dpi=180, metadata={"Date": None} if extension == "svg" else None)
    plt.close(fig)
    svg = output / "obstacle_handoffs.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    assert all(sha256_file(Path(p)) == digest for p, digest in before.items())
    assert all(sha256_file(run / name) == digest for name, digest in recorded.items())
    write_json(output / "plot_manifest.json", {
        "source_run": str(run), "source_audit": str(audit), "panels": manifests,
        "purpose": "Retrospective illustration; no new correspondence or candidate selection",
        "world_anchor": "Each prediction's observation pose; never switch pose",
        "unchanged_verdict": "NO_QUALIFIED_CANDIDATE",
        "checks": {"all_run_hashes_unchanged": len(recorded), "plot_input_hashes_unchanged": True,
                   "observation_world_coordinates_match": True, "switch_pose_and_interval_match": True},
        "input_sha256": before, "plot_source_sha256": sha256_file(Path(__file__)),
        "output_sha256": {p.name: sha256_file(p) for p in sorted(output.glob("obstacle_handoffs.*"))}})
    print(output / "obstacle_handoffs.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    base = ROOT.parent / "artifacts/isaac6"
    parser.add_argument("--run", type=Path, default=base / "async_wide_wall_01")
    parser.add_argument("--audit", type=Path, default=base / "async_handoff_audit_01")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.run.resolve(), args.audit.resolve(), args.output.resolve())
