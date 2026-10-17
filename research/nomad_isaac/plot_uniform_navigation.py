"""Plot recorded uniform-latency executions without running NoMaD or Isaac Sim."""
import argparse
import json
from pathlib import Path

import numpy as np

from .common import sha256_file, write_json
from .clearance import configured_obstacles, obstacle_bounds, single_obstacle_config


def plot(results, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Patch, Rectangle

    source = results / "summary.json"
    summaries = json.loads(source.read_text())
    conditions = ["D0", "D250", "D500", "D750"]
    hashes = {str(source): sha256_file(source)}
    data, checks = {}, {}
    for condition in conditions:
        summary = summaries[condition]
        run = Path(summary["source_run"])
        manifest = results / condition / "input_hashes.json"
        hashes[str(manifest)] = sha256_file(manifest)
        recorded = json.loads(manifest.read_text())
        for name, digest in recorded.items():
            assert sha256_file(run / name) == digest
            hashes[str(run / name)] = digest
        raw = json.loads((run / "summary.json").read_text())
        config = json.loads((run / "scenario.json").read_text())
        trace = np.genfromtxt(run / "agent_trajectory.csv", delimiter=",", names=True)
        poses = np.column_stack([trace[key] for key in ("x_m", "y_m", "yaw_rad")])
        times = trace["simulation_time_s"]
        assert config == raw["scenario"]
        if data:
            assert config == data["D0"][0]
        np.testing.assert_allclose(poses[0], config["start_pose"], atol=1e-12, rtol=0)
        np.testing.assert_allclose(poses[-1], summary["navigation"]["final_pose"], atol=1e-12, rtol=0)
        np.testing.assert_allclose(np.diff(times), 1/config["integration_hz"], atol=1e-12, rtol=0)
        goal_distances = np.linalg.norm(poses[:, :2]-config["goal_pose"][:2], axis=1)
        assert abs(goal_distances.min()-summary["navigation"]["minimum_goal_distance_m"]) < 1e-12
        assert abs(times[-1]-summary["navigation"]["simulation_duration_s"]) < 1e-12
        assert bool(np.any(goal_distances <= config["goal_tolerance_m"])) == raw["goal_entry"]
        data[condition] = (config, poses, times)
        checks[condition] = {"run": str(run), "pose_rows": len(poses), "final_pose": poses[-1].tolist(),
                             "end_sim_s": float(times[-1]), "goal_entry": raw["goal_entry"],
                             "termination_reason": raw["termination_reason"], "input_hash_count": len(recorded)}

    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "svg.fonttype": "none", "svg.hashsalt": "nomad-uniform-navigation",
                         "path.simplify": False})
    route, obstacle, goal_color = "#215dac", "#a8cf9d", "#b47b0c"
    end_color, wall = "#bb3347", "#596674"
    handles = [Line2D([], [], color=route, lw=2.5, label="Executed center path"),
               Line2D([], [], marker="o", color="#202b37", ls="none", label="Start"),
               Line2D([], [], marker="*", color=goal_color, ls="none", ms=12, label="Goal (tolerance 0.30 m)"),
               Line2D([], [], marker="x", color=end_color, ls="none", ms=8, label="Final pose + 0.09 m footprint"),
               Patch(facecolor=obstacle, edgecolor="#4e7c43", label="Static obstacles"),
               Line2D([], [], color=wall, ls="--", lw=1, label="Center limit: wall minus radius")]

    def panel(ax, condition):
        config, poses, times = data[condition]
        summary = summaries[condition]
        nav = summary["navigation"]
        width, radius = config["corridor"]["half_width"], config["agent_radius_m"]
        for side in (-1, 1):
            ax.axhspan(*sorted([side*width, side*1.72]), color="#e9edf1", zorder=0)
            ax.axhline(side*width, color=wall, lw=1.4, zorder=1)
            ax.axhline(side*(width-radius), color=wall, lw=.9, ls="--", alpha=.65, zorder=1)
        for index, box in enumerate(configured_obstacles(config), 1):
            low, high = obstacle_bounds(single_obstacle_config(config, box))
            ax.add_patch(Rectangle(low, *(high-low), fc=obstacle, ec="#4e7c43", lw=1.2, zorder=2))
            ax.text(*box["center_xy_m"], f"O{index}", ha="center", va="center", fontsize=10,
                    color="#244620", weight="bold", zorder=3)
        goal = config["goal_pose"][:2]
        ax.add_patch(Circle(goal, config["goal_tolerance_m"], fc="#f6e5b9", ec=goal_color, lw=.8, alpha=.7, zorder=2))
        ax.plot(*poses[:, :2].T, color=route, lw=2.4, zorder=4)
        distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(poses[:, :2], axis=0), axis=1))]
        for fraction in (.25, .55, .80):
            i = min(int(np.searchsorted(distance, fraction*distance[-1])), len(poses)-1)
            j = min(int(np.searchsorted(distance, distance[i]+.13)), len(poses)-1)
            ax.annotate("", xy=poses[j, :2], xytext=poses[i, :2],
                        arrowprops={"arrowstyle": "-|>", "color": route, "lw": 1.5, "mutation_scale": 12}, zorder=5)
        ax.scatter(*poses[0, :2], s=40, c="#202b37", zorder=6)
        ax.text(-.02, -.23, "Start", ha="center", fontsize=9)
        ax.scatter(*goal, marker="*", s=135, c=goal_color, zorder=6)
        ax.text(goal[0], -.48, "Goal", ha="center", color="#88600d", fontsize=9)
        final = poses[-1, :2]
        ax.add_patch(Circle(final, radius, fill=False, ec=end_color, lw=1.4, zorder=6))
        ax.scatter(*final, marker="x", s=55, c=end_color, lw=1.8, zorder=7)
        if nav["goal_entry"]:
            label, target = "Goal entry", (3.65, -.83)
        elif final[1] < 0:
            label, target = "Corridor footprint breach", (2.15, -.98)
        else:
            label, target = "Corridor footprint breach", (.02, 1.12)
        ax.annotate(label, final, xytext=target, fontsize=9, color=end_color,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9, "pad": 2},
                    arrowprops={"arrowstyle": "->", "color": end_color, "lw": .9}, zorder=8)
        suffix = " (historical reference)" if condition == "D0" else ""
        status = "GOAL REACHED" if nav["goal_entry"] else "CORRIDOR EXIT"
        ax.set_title(f"{condition} | +{round(summary['configured_delay_s']*1000)} ms{suffix}\n"
                     f"{status}  |  {times[-1]:.2f} s  |  min goal distance {nav['minimum_goal_distance_m']:.3f} m",
                     loc="left", fontsize=10.5, pad=12, linespacing=1.65)
        ax.set(xlim=(-.45, 5.0), ylim=(-1.72, 1.72), xlabel="World X (m)", ylabel="World Y (m)", aspect="equal")
        ax.set_xticks(np.arange(0, 5.1, 1)); ax.set_yticks(np.arange(-1.5, 1.51, .5))
        ax.grid(alpha=.16, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)

    def save(fig, name):
        fig.savefig(output/f"{name}.png", dpi=180, facecolor="white")
        svg = output/f"{name}.svg"
        fig.savefig(svg, metadata={"Date": None}, facecolor="white")
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
        plt.close(fig)

    for condition in conditions:
        fig, ax = plt.subplots(figsize=(9.2, 7.0))
        fig.subplots_adjust(left=.09, right=.97, top=.86, bottom=.22)
        panel(ax, condition)
        fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, .055), ncol=2,
                   frameon=False, fontsize=9, columnspacing=2.5)
        fig.text(.5, .02, "Recorded 72 Hz poses; arrows show travel direction. No navigation or inference rerun.",
                 ha="center", fontsize=8.5, color="#58616b")
        save(fig, f"{condition}_world_xy")
    fig, axes = plt.subplots(2, 2, figsize=(14.4, 11.1))
    fig.subplots_adjust(left=.06, right=.98, top=.89, bottom=.16, wspace=.17, hspace=.44)
    for ax, condition in zip(axes.flat, conditions):
        panel(ax, condition)
    fig.suptitle("NoMaD | Full-run uniform delivery latency", fontsize=19, weight="bold", y=.98)
    fig.text(.5, .939, "Recorded world-XY execution | Same geometry and axis limits in every panel",
             ha="center", fontsize=11, color="#58616b")
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, .065), ncol=3,
               frameon=False, fontsize=10, columnspacing=2.)
    fig.text(.5, .027, "D0 is a historical reference; D250/D500/D750 were each run once. No paired causal claim.\n"
             "All delayed runs stopped at a corridor footprint breach; no obstacle overlap was recorded.",
             ha="center", fontsize=9.5, color="#58616b", linespacing=1.5)
    save(fig, "uniform_navigation_comparison")
    assert all(sha256_file(Path(path)) == digest for path, digest in hashes.items())
    write_json(output/"manifest.json", {"conditions": checks, "input_sha256": hashes,
               "checks": "Input hashes, start/end pose, 72 Hz times, goal entry and minimum goal distance verified",
               "new_navigation_runs": 0, "new_inference_calls": 0, "trajectory_smoothing": False,
               "world_limits_m": {"x": [-.45, 5.], "y": [-1.72, 1.72]},
               "source_sha256": sha256_file(Path(__file__)),
               "output_sha256": {p.name: sha256_file(p) for p in sorted(output.iterdir()) if p.suffix in (".png", ".svg")}})
    print(json.dumps({"output": str(output), "conditions": conditions, "verified_inputs": len(hashes)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.results.resolve(), args.output.resolve())
