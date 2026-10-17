"""Offline audit of the one actual-OLD placement pilot. No navigation or inference."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .async_report import rows, validate
from .clearance import first_contact_bracket, obstacle_bounds, single_obstacle_config
from .common import sha256_file, write_json
from .old_rollout_placement import place_on_old
from .sudden_obstacle_report import analyze


def equivalent(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a: equivalent(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b): equivalent(x, y)
    elif isinstance(a, (float, int)) and not isinstance(a, bool):
        np.testing.assert_allclose(a, b, atol=1e-10, rtol=0)
    else:
        assert a == b, (a, b)


def report(run, output, preservation):
    output.mkdir(parents=True, exist_ok=False)
    preserved = json.loads(preservation.read_text())
    assert all(sha256_file(Path(p)) == h for p, h in preserved.items())
    raw = json.loads((run/"summary.json").read_text()); config = raw["scenario"]
    decision = raw["dynamic_obstacle"]["placement"]
    if raw["dynamic_obstacle"]["status"] != "SPAWNED":
        runtime = validate(run, run.parent/"two_obstacles_01", output/"runtime_validation")
        result = {"placement_status": raw["dynamic_obstacle"]["status"], "placement": decision,
                  "classification": "INSUFFICIENT_EVIDENCE", "graph_verdict": "INSUFFICIENT_EVIDENCE",
                  "reason": "No dynamic obstacle was spawned; no OLD/FRESH obstacle reaction pair",
                  "runtime": runtime, "navigation": raw}
        write_json(output/"summary.json", result)
        return result
    native = analyze(run, output/"handoff", preservation_manifest=preservation)
    spawn = native["spawn"]; old_id = spawn["old_id"]
    received = rows(run/"received.jsonl")
    old = next(r for r in received if r["id"] == old_id)
    remaining = 1.-(spawn["monotonic_ns"]-old["received_monotonic_ns"])/1e9
    assert abs(remaining-decision["old_remaining_timeout_s"]) < 1e-12
    recreated = place_on_old(config, spawn["pose"], *spawn["old_command_vw"], old_id,
                             spawn["old_command_valid"], remaining)
    equivalent(recreated, {k: decision[k] for k in recreated})
    assert decision["status"] == "PLACED" and spawn["tick"] == config["dynamic_obstacle"]["spawn_tick"]
    controls = rows(run/"controller.jsonl")
    previous = [c for c in controls if c["simulation_time_s"] < spawn["simulation_time_s"]][-1]
    assert previous["waypoint_id"] == old_id and previous["valid"]
    np.testing.assert_allclose([previous["v_m_s"], previous["w_rad_s"]], spawn["old_command_vw"], rtol=0, atol=0)
    update = json.loads((run/"dynamic_render_update.json").read_text())
    assert update["obstacle"] == decision["obstacle"] == spawn["obstacle"]
    lower, upper = obstacle_bounds(single_obstacle_config(config, spawn["obstacle"]))
    np.testing.assert_allclose(update["usd_aabb"], [[*lower, 0.], [*upper, .8]], rtol=0, atol=1e-12)
    active_observations = [o for o in rows(run/"observations.jsonl") if o.get("dynamic", {}).get("active")]
    if active_observations:
        assert update["applied_host_ns"] <= active_observations[0]["observation_monotonic_ns"]
        assert update["snapshot_tick"] == active_observations[0]["dynamic"]["capture_tick"]
    candidate = decision["candidates"][decision["selected_candidate_index"]]
    contact = first_contact_bracket(spawn["pose"], *spawn["old_command_vw"], remaining,
                                    lower, upper, config["agent_radius_m"])
    assert contact["offset_bracket_s"][0] >= config["dynamic_obstacle"]["placement"]["reaction_budget_s"]
    assert contact["offset_bracket_s"][1] <= remaining
    old_unsafe = candidate["timeout_clipped_rollout"]["geometric_overlap"]
    fresh_safe = native["fresh_safety"]["all_obstacles"]["full"]["safe"] if native["fresh_safety"] else None
    collision = native["pre_fresh_execution"]["dynamic_geometric_overlap"]
    classification = ("OLD_EXECUTION_COLLISION" if collision else "INSUFFICIENT_EVIDENCE" if fresh_safe is None else
                      "UNSAFE_OLD_SAFE_FRESH" if old_unsafe and fresh_safe else
                      "UNSAFE_OLD_UNSAFE_FRESH" if old_unsafe else
                      "OLD_SAFE_FRESH_SAFE" if fresh_safe else "INSUFFICIENT_EVIDENCE")
    timing = native["timing"]
    switch_delay = ((timing["switch_host_ns"]-spawn["monotonic_ns"])/1e9 if native["fresh_applied"] else None)
    visible_delay = ((timing["first_visible_capture_host_ns"]-spawn["monotonic_ns"])/1e9
                     if timing["first_visible_capture_host_ns"] else None)
    result = {"source_run": str(run), "execution_git_sha": native["execution_git_sha"],
              "placement_status": decision["status"], "placement": decision,
              "placement_computation_ms": (decision["computation_end_ns"]-decision["computation_start_ns"])/1e6,
              "counterfactual_first_contact": contact, "render_update": update,
              "old_controller_rollout_unsafe": old_unsafe, "first_fresh_full_safe": fresh_safe,
              "classification": classification, "graph_verdict": native["graph_verdict"],
              "handoff_classification": native["geometry"]["classification"] if native["geometry"] else None,
              "spawn_to_first_visible_capture_wall_s": visible_delay, "spawn_to_switch_wall_s": switch_delay,
              "fresh_switch_within_reaction_budget": switch_delay <= config["dynamic_obstacle"]["placement"]["reaction_budget_s"] if switch_delay is not None else None,
              "first_post_visible_safe_full_id": next(iter(native["post_visible_safe_full_prediction_ids"]), None),
              "old_id": old_id, "fresh_id": native["fresh_id"], "fresh_applied": native["fresh_applied"],
              "native_audit": native,
              "validation": {"placement_recomputed_from_current_applied_old": "PASS", "remaining_old_timeout_clock": "PASS",
                  "render_and_collision_same_geometry": "PASS", "raw_history_hashes": "PASS",
                  "prior_inputs_preserved": len(preserved), "new_navigation_count_for_analysis": 0},
              "limitations": ["One fixed-rule pilot; no counterfactual execution", "Local empty strip is not a guaranteed PD bypass",
                  "0.55 s reaction budget is predeclared, not added delay or guaranteed inference deadline",
                  "Native predictions and held-command arc are different; predictions have no native yaw/time",
                  "Different observation histories and diffusion seeds confound causal obstacle-response claims",
                  "First visible FRESH retained even if unsafe; no tuning, Graph, Topomap, or new controller"]}
    # Explain the eventual outcome without attributing later commands to the
    # first FRESH or replacing it with a retrospectively favorable prediction.
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True, dtype=None, encoding="utf-8")
    dynamic_rows = rows(run/"dynamic/clearance.jsonl")
    events = rows(run/"events.jsonl")
    predictions = {int(r["id"]): r for r in csv.DictReader((output/"handoff/predictions.csv").open())}
    applied_segments = []
    spawn_tick = spawn["tick"]; hz = config["integration_hz"]
    for i, e in enumerate(events):
        if e["id"] < old_id: continue
        start = max(spawn_tick, round(e["application_sim_s"]*hz))
        end = round(events[i+1]["application_sim_s"]*hz) if i+1 < len(events) else len(trace)-1
        if end <= start: continue
        indices = list(range(start+1, end+1))
        assert set(map(int, trace["incoming_waypoint_id"][indices])) == {e["id"]}
        checks = [dynamic_rows[j-spawn_tick] for j in indices]
        p = predictions[e["id"]]
        applied_segments.append({"id": e["id"], "start_sim_s": start/hz, "end_sim_s": end/hz,
            "v_m_s": e["v_m_s"], "w_rad_s": e["w_rad_s"],
            "native_dynamic_full_m": float(p["dynamic_only_full_obstacle_clearance_m"]),
            "native_dynamic_prefix_m": float(p["dynamic_only_prefix_obstacle_clearance_m"]),
            "executed_dynamic_clearance_lower_m": min(c["lower_m"] for c in checks),
            "executed_dynamic_overlap": any(c["geometric_overlap"] for c in checks)})
    unsafe = next((r for r in dynamic_rows if r["lower_m"] < config["required_clearance_m"]), None)
    first_contact = raw["dynamic_obstacle"]["evaluation"]["first_contact"]
    contact_tick = round(first_contact["detected_sim_s"]*hz) if first_contact else None
    collision_wall = int(trace["monotonic_ns"][contact_tick]) if contact_tick is not None else None
    result["later_execution"] = {"applied_segments": applied_segments,
        "first_safety_margin_breach": None if unsafe is None else {
            "interval_end_sim_s": unsafe["end_sim_s"], "clearance_lower_m": unsafe["lower_m"],
            "command_id": int(trace["incoming_waypoint_id"][round(unsafe["end_sim_s"]*hz)])},
        "collision_command_id": int(trace["incoming_waypoint_id"][contact_tick]) if contact_tick is not None else None,
        "gpu_requests_in_progress_at_collision": [r["id"] for r in received if collision_wall and
            r["inference_start_monotonic_ns"] <= collision_wall < r["ready_monotonic_ns"]],
        "terminal_unapplied_ids": [r["id"] for r in received if r["terminal_unapplied"]],
        "first_contact": first_contact,
        "scope": "Later commands and pending FRESH are separate from the spawn OLD / first-visible FRESH pair"}
    plot(result, config, run, output)
    assert all(sha256_file(Path(p)) == h for p, h in preserved.items())
    hashes = json.loads((output/"handoff/input_hashes.json").read_text())
    assert all(sha256_file(run/p) == h for p, h in hashes.items())
    result["validation"]["new_run_inputs_preserved"] = len(hashes)
    write_json(output/"summary.json", result)
    print(json.dumps({k: result[k] for k in ("old_id", "fresh_id", "classification", "graph_verdict")}))
    return result


def plot(result, config, run, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Rectangle

    audit = result["native_audit"]; decision = result["placement"]
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True)
    xy = np.column_stack([trace["x_m"], trace["y_m"]])
    old = np.array(audit["old_world_xy_m"]); fresh = np.array(audit["fresh_world_xy_m"]) if audit["fresh_id"] is not None else None
    rollout = np.array(decision["rollout_pose"])[:, :2]
    center = decision["obstacle"]["center_xy_m"]
    plt.rcParams.update({"font.family":"DejaVu Sans", "svg.fonttype":"none", "path.simplify":False})
    fig, axes = plt.subplots(1,2,figsize=(13,6))
    fig.subplots_adjust(left=.055,right=.98,top=.82,bottom=.22,wspace=.20)
    for ax in axes:
        for box in [*config["obstacles"],decision["obstacle"]]:
            lo,hi=obstacle_bounds(single_obstacle_config(config,box))
            ax.add_patch(Rectangle(lo,*(hi-lo),fc="#b226a0" if box["id"]=="DynamicObstacle" else "#9bc68a",alpha=.6,zorder=1))
        ax.plot(*xy.T,c="#737b83",lw=1.8,zorder=2)
        ax.plot(*old.T,"o-",c="#c27608",ms=3,lw=2,zorder=4)
        ax.scatter(*old[2],marker="s",c="#c27608",s=45,zorder=5)
        if fresh is not None:
            ax.plot(*fresh.T,"o-",c="#2167b1",ms=3,lw=2,zorder=4)
            ax.scatter(*fresh[2],marker="s",c="#2167b1",s=45,zorder=5)
        ax.plot(*rollout.T,"--",c="#d32f3d",lw=3,zorder=6)
        ax.add_patch(Circle(rollout[-1],config["agent_radius_m"],fc="#d32f3d",alpha=.12,
                            ec="#d32f3d",ls="--",zorder=3))
        ax.scatter(*xy[-1],marker="x",c="#343b42",s=45,zorder=9)
        ax.scatter(*audit["spawn"]["pose"][:2],marker="^",s=70,c="#d32f3d",zorder=8)
        if audit["fresh_applied"]:
            b=audit["boundary_pose"][:2]
            ax.scatter(*b,marker="D",c="black",s=35,zorder=9)
            ax.add_patch(Circle(b,config["agent_radius_m"],fill=False,ec="black",lw=.8,zorder=3))
            entry=audit["geometry"]["entry"].get("chosen") or audit["geometry"]["entry"].get("nearest")
            if entry:
                p=entry["xy_m"];ax.plot([b[0],p[0]],[b[1],p[1]],":",c="#7927a2",lw=2,zorder=6)
                ax.scatter(*p,marker="x",c="#7927a2",s=50,zorder=9)
        ax.set_aspect("equal");ax.grid(alpha=.18);ax.set_xlabel("World X (m)");ax.set_ylabel("World Y (m)")
    axes[0].set(xlim=(-.2,4.95),ylim=(-1.6,1.6));axes[0].set_title("Recorded execution and fixed scene",loc="left",fontsize=11)
    for wall in (-1.5,1.5):axes[0].axhline(wall,c="#4c5660",lw=1)
    axes[0].scatter(*config["start_pose"][:2],c="#262b31",s=40)
    axes[0].add_patch(Circle(config["goal_pose"][:2],config["goal_tolerance_m"],fill=False,ec="#d78a0a"))
    axes[0].scatter(*xy[-1],marker="x",c="#262b31",s=50)
    points=np.vstack([old, rollout, np.array(center).reshape(1,2), fresh if fresh is not None else old])
    lo=points.min(0)-.25;hi=points.max(0)+.25;span=max(hi-lo);mid=(lo+hi)/2
    axes[1].set(xlim=(mid[0]-span/2,mid[0]+span/2),ylim=(mid[1]-span/2,mid[1]+span/2))
    axes[1].set_title(f"Spawn OLD {audit['old_id']} / first visible FRESH {audit['fresh_id']}",loc="left",fontsize=11)
    axes[1].annotate("Counterfactual OLD footprint\nat remaining timeout", rollout[-1],
                     (mid[0]+.06,mid[1]+span*.31),fontsize=8,color="#bc2338",
                     arrowprops={"arrowstyle":"->","color":"#bc2338","lw":.8})
    collision_id=result["later_execution"]["collision_command_id"]
    if collision_id is not None:
        axes[1].annotate(f"Actual collision\nunder later command {collision_id}",xy[-1],
                        (lo[0]+.04,mid[1]-.18),fontsize=8,color="#343b42",
                        arrowprops={"arrowstyle":"->","color":"#343b42","lw":.8})
    handles=[Line2D([],[],c="#737b83",label="Actual executed center path"),
             Line2D([],[],c="#d32f3d",ls="--",lw=3,label="OLD held-command rollout (until timeout)"),
             Line2D([],[],c="#c27608",marker="o",label="Native OLD (observation anchored)"),
             Line2D([],[],c="#2167b1",marker="o",label="Native FRESH (observation anchored)"),
             Line2D([],[],c="#d32f3d",marker="^",ls="none",label="Actual spawn pose"),
             Line2D([],[],c="black",marker="D",ls="none",label="Actual switch B / 9 cm footprint")]
    fig.suptitle("Actual OLD rollout obstacle pilot",fontsize=17,weight="bold",y=.97)
    fig.text(.5,.91,f"{result['classification']}  |  Graph evidence: {result['graph_verdict']}",ha="center",fontsize=11)
    fig.legend(handles=handles,ncol=3,loc="lower center",bbox_to_anchor=(.5,.065),fontsize=8.5,frameon=False)
    fig.text(.5,.025,"Dashed red is counterfactual, not executed motion. Squares: selected index 2. Dotted connector is an offline diagnostic; no Graph or smoothing.",ha="center",fontsize=8)
    fig.savefig(output/"old_rollout_handoff.png",dpi=180,facecolor="white")
    svg=output/"old_rollout_handoff.svg";fig.savefig(svg,metadata={"Date":None},facecolor="white")
    svg.write_text("\n".join(s.rstrip() for s in svg.read_text().splitlines())+"\n");plt.close(fig)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--preservation",type=Path,required=True)
    args=parser.parse_args();report(args.run.resolve(),args.output.resolve(),args.preservation.resolve())
