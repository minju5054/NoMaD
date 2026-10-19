"""Audit the unchanged graph's heading gate and the authorized B52 controls.

No substitute yaw or relaxed gate: this frozen input is rejected before a solve.
The original graph rollout kernel is reused without constructing invalid SE2 nodes.
"""
import argparse
import csv
import json
from pathlib import Path
import platform
import subprocess
from types import SimpleNamespace

import numpy as np
import scipy

from .common import ROOT, local_to_world, original_controller, sha256_file, write_json
from .clearance import configured_obstacles, obstacle_bounds, point_clearance, single_obstacle_config
from .handoff_audit import path_safety
from .minimal_se2_graph import Experiment, derived_headings, local_point, validate_actual_after_solve


def command_detail(point):
    dx, dy = point
    if abs(dx) < 1e-8:
        unclipped = [0., float(np.sign(dy)*np.pi/(2*.25))]
    else:
        unclipped = [float(dx/.25), float(np.arctan(dy/dx)/.25)]
    command = [float(x) for x in original_controller()(point)]
    return {"local_waypoint": point.tolist(), "unclipped_vw": unclipped, "command_vw": command,
            "v_clipped": command[0] != unclipped[0], "w_clipped": command[1] != unclipped[1]}


def plot(out, context, old, fresh, observation, results, heading_gate):
    # Layout and rounded-AABB contour construction reuse the original graph plot.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    plt.rcParams.update({"svg.fonttype":"none", "svg.hashsalt":"topomap-b52-graph-gate", "path.simplify":False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5), gridspec_kw={"width_ratios":[1, 1.15]})
    colors = {"RAW":"#d1495b", "UNCHANGED-B-LOCAL":"#2274b9", "STOP":"#3f4b56"}
    for ax in axes:
        for key, (lo, hi) in context.boxes.items():
            ax.add_patch(Rectangle(lo, *(hi-lo), color="#bd57ac" if key == "DynamicObstacle" else "#789a77", alpha=.30))
        gx=np.linspace(2.08,2.65,450); gy=np.linspace(-.1,.70,500)
        xx, yy=np.meshgrid(gx,gy);lo,hi=context.boxes["DynamicObstacle"]
        distance=np.sqrt(np.maximum(np.maximum(lo[0]-xx,xx-hi[0]),0)**2 + np.maximum(np.maximum(lo[1]-yy,yy-hi[1]),0)**2)
        ax.contour(xx,yy,distance,levels=[context.radius,context.radius+.02],colors=["#952c83"]*2,
                   linestyles=[":","--"],linewidths=1)
        ax.plot(*context.boundary[:2],"k*",ms=12,zorder=10,label="B52 fixed")
        ax.set_aspect("equal");ax.grid(alpha=.15);ax.set_xlabel("World X (m)");ax.set_ylabel("World Y (m)")
    axes[0].plot(*old.T,":",c=".65",lw=1.3,label="OLD51: context only")
    axes[0].plot(*fresh.T,"o--",c="#2274b9",ms=4,lw=1.7,label="Unchanged FRESH52 native XY")
    axes[0].plot(*fresh[2],"s",c="#2274b9",ms=6,label="Index 2 world point")
    axes[0].plot(*observation[:2],"kx",ms=6,label="Observation pose")
    axes[0].plot(*fresh[:2].T,c="#c63d40",lw=4,zorder=5)
    axes[0].annotate(f"Segment 0: {1000*heading_gate['segment_lengths_m'][0]:.3f} mm < 20 mm\nFirst heading INVALID",
                     fresh[:2].mean(0),(2.12,.66),fontsize=9,color="#b23137",
                     arrowprops={"arrowstyle":"->","color":"#b23137"})
    axes[0].text(2.37,.10,"Dynamic obstacle\n0.35 x 0.35 m",ha="center",fontsize=10,color="#713d69")
    for name in ("RAW","UNCHANGED-B-LOCAL","STOP"):
        roll=results[name]["rollout"];trace=np.asarray(roll["poses"]);c=colors[name]
        for ax in axes:
            ax.plot(*trace[:,:2].T,color=c,lw=3,zorder=6,
                    label=f"{name}: {100*roll['minimum_clearance_m']:.3f} cm" if ax is axes[1] else None)
        axes[1].plot(*trace[-1,:2],"o",c=c,ms=5,zorder=7)
        axes[1].add_patch(Circle(trace[-1,:2],context.radius,fill=False,color=c,lw=1.2,alpha=.85))
    axes[0].set(xlim=(2.10,2.64),ylim=(-.1,.71),title="Original XY; no rigid or graph correction")
    axes[1].set(xlim=(2.18,2.47),ylim=(.27,.535),title="Same B52 + original PD, 16/72 s")
    axes[0].legend(loc="lower left",fontsize=8)
    axes[1].legend(loc="upper left",fontsize=8)
    axes[1].text(.04,.04,"RIGID / GRAPH: NOT RUN\nOriginal initial-heading gate rejected input",
                 transform=axes[1].transAxes,fontsize=9,bbox={"facecolor":"white","edgecolor":"none","alpha":.9})
    fig.suptitle("Topomap OLD51 -> FRESH52: unchanged SE(2) graph preflight",fontsize=15)
    fig.text(.5,.055,"RAW matches recorded execution. UNCHANGED-B-LOCAL and STOP are offline counterfactuals.\nPurple dotted / dashed: contact / 2 cm footprint-center limits. No native yaw or waypoint timestamps.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.12,1,.94))
    fig.savefig(out/"comparison.png",dpi=180,facecolor="white")
    svg=out/"comparison.svg";fig.savefig(svg,metadata={"Date":None},facecolor="white")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True);parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();run=args.run.resolve();out=args.out.resolve()
    plan_path=Path(__file__).with_name("topomap_b52_graph_protocol.json")
    plan=json.loads(plan_path.read_text());base_path=plan_path.with_name(plan["inherited_protocol"])
    original=json.loads(base_path.read_text())
    for name,digest in plan["unchanged_reused_files_sha256"].items():assert sha256_file(ROOT/name)==digest
    p={**original,"old_id":51,"fresh_id":52,"boundary_tick":1016}
    assert p["horizon_ticks"]==16 and p["minimum_heading_segment_m"]==.02
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/"protocol.json",plan)
    audit=run.parent/"topomap_sudden_01_validation"
    hashes=json.loads((audit/"input_hashes.json").read_text())
    assert all(sha256_file(run/name)==h for name,h in hashes.items())
    before={str(f.relative_to(ROOT)):sha256_file(f) for f in (Path(__file__).resolve(),plan_path.resolve(),base_path.resolve(),
             ROOT/"research/nomad_isaac/minimal_se2_graph.py",ROOT/"research/nomad_isaac/common.py",
             ROOT/"research/nomad_isaac/clearance.py",ROOT/"deployment/src/pd_controller.py")}
    events={}
    with (run/"events.jsonl").open() as stream:
        for line in stream:
            event=json.loads(line)
            if event["id"] in (51,52):events[event["id"]]=event
            if event["id"]==52:break
    assert set(events)=={51,52}
    e=events[52];boundary=np.array(e["agent_pose_at_switch"])
    assert e["application_sim_s"]==1016/72 and e["observation_sim_s"]==1007/72
    np.testing.assert_allclose(boundary,[2.294383156,.399014947,-.636309015],rtol=0,atol=1e-9)
    with (run/"agent_trajectory.csv").open() as stream:
        for row in csv.DictReader(stream):
            if int(row["tick"])==1016:
                np.testing.assert_array_equal(boundary,[float(row[k]) for k in ("x_m","y_m","yaw_rad")]);break
    config=json.loads((run/"scenario.json").read_text());spawn=json.loads((run/"dynamic/spawn.json").read_text())
    assert spawn["tick"]<1016
    config["obstacles"]=[*config["obstacles"],spawn["obstacle"]]
    assert config["agent_radius_m"]==p["radius_m"]==.09 and config["required_clearance_m"]==p["required_clearance_m"]==.02
    worlds={};local={}
    for i in (51,52):
        with np.load(run/f"model/derived/{i:04d}.npz",allow_pickle=False) as z:
            assert z["metric"].shape==(8,8,2)
            local[i]=z["metric"][0].astype(float)
        worlds[i]=local_to_world(local[i],events[i]["observation_pose"])
    xy=worlds[52]
    # Apply the exact original gate before forming any future SE2 poses.
    heading,lengths=derived_headings(xy)
    valid=np.r_[lengths>=p["minimum_heading_segment_m"],lengths[-1]>=p["minimum_heading_segment_m"]]
    gate={"status":"PASS" if valid.all() else "INVALID_INITIAL_HEADING",
          "minimum_segment_m":p["minimum_heading_segment_m"],"segment_lengths_m":lengths.tolist(),
          "invalid_segments":np.flatnonzero(lengths<.02).tolist(),"valid_node_headings":valid.tolist(),
          "derived_heading_rad":[float(h) if ok else None for h,ok in zip(heading,valid)],
          "rule":"outgoing tangent nodes0..6, last incoming at7; reject ANY invalid initial segment"}
    write_json(out/"heading_gate.json",gate)
    # This audit deliberately never substitutes a heading or relaxes this rejection.
    assert not valid.all(), "Unexpected input: this rejection audit must not silently start a solve"
    solver={"status":"NOT_RUN_INVALID_INITIAL_HEADING","calls":0,"converged":None,"cost":None,
            "residual_l2":None,"factor_costs":None,"cpu_wall_s":None,
            "reason":"F0->F1 = 0.017282994059m < unchanged 0.020m minimum; F0 yaw unavailable"}
    write_json(out/"solver.json",solver)
    write_json(out/"inputs.json",{"boundary":boundary.tolist(),"observation_pose":e["observation_pose"],
        "fresh_local_sample0":local[52].tolist(),"fresh_world_xy":xy.tolist(),"geometry":config["obstacles"],
        "corridor":config["corridor"],"source_sha256":before,"original_protocol_sha256":sha256_file(base_path),
        "branch_sha":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "environment":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
        "no_fresh53_or_later_outcome_inputs":True})
    # Exact original graph rollout method needs only these fields, not future pose headings.
    context=SimpleNamespace(boundary=boundary,config=config,p=p,dt=1/72,radius=.09,
        boxes={b["id"]:obstacle_bounds(single_obstacle_config(config,b)) for b in configured_obstacles(config)})
    native={"full":path_safety(xy,config),"prefix":path_safety(xy[:3],config),
            "boundary_prefix":path_safety(np.vstack([boundary[:2],xy[:3]]),config)}
    results={}
    raw_pd=command_detail(local[52][2])
    np.testing.assert_array_equal(raw_pd["command_vw"],[e["v_m_s"],e["w_rad_s"]])
    np.testing.assert_allclose(raw_pd["command_vw"],[.166895986,.4],rtol=0,atol=1e-9)
    raw_roll=Experiment.rollout(context,raw_pd["command_vw"])
    np.testing.assert_allclose(raw_roll["minimum_clearance_m"],.002653804,rtol=0,atol=1e-9)
    np.testing.assert_allclose(native["full"]["obstacle_clearance_m"],.026484613,rtol=0,atol=1e-9)
    # Terminal gate decision is already saved. Future trace is validation only and is not
    # supplied to the controls, any optimizer, or parameter choice. No solve was invoked.
    validation=validate_actual_after_solve(run,context,{"rollout":raw_roll})
    validation.pop("future_trace_read_only_after_solve")
    validation["future_trace_read_after_terminal_heading_rejection"]=True
    with (run/"agent_trajectory.csv").open() as stream:
        for row in csv.DictReader(stream):
            tick=int(row["tick"])
            if 1016<tick<=1032:assert int(row["incoming_waypoint_id"])==52
            if tick>=1032:break
    for name,point in (("RAW",local[52][2]),("UNCHANGED-B-LOCAL",local_point(xy[2],boundary))):
        command=raw_pd if name=="RAW" else command_detail(point)
        results[name]={"status":"EVALUATED","controller":command,"native":native,
            "boundary_position_m":float(np.linalg.norm(xy[0]-boundary[:2])),"boundary_tangent_heading_deg":None,
            "trajectory_position_change_rms_m":0.,"trajectory_heading_change_deg":None,
            "relative_transform_error":None,"relative_transform_note":"No complete SE2 chain: first-node heading invalid; XY unchanged",
            "rollout":raw_roll if name=="RAW" else Experiment.rollout(context,command["command_vw"])}
    for name in ("RIGID","GRAPH"):
        results[name]={"status":"NOT_RUN_INVALID_INITIAL_HEADING","controller":None,"rollout":None,"native":None,
                       "reason":"Original rigid alignment/graph requires valid first future pose heading"}
    results["STOP"]={"status":"TRIVIAL_REFERENCE","controller":{"local_waypoint":None,"unclipped_vw":None,
        "command_vw":[0.,0.],"v_clipped":None,"w_clipped":None},"native":None,"rollout":Experiment.rollout(context,[0.,0.])}
    # Prior Graph results are descriptive references, opened only after terminal gating.
    reference_path="research/results/isaac6_minimal_se2_graph_20261019/summary.json"
    reference_blob=subprocess.check_output(["git","show",plan["graph_source_commit"]+":"+reference_path],cwd=ROOT)
    reference=json.loads(reference_blob)
    fixed={"source_commit":plan["graph_source_commit"],"source_file":reference_path,
           "solver":reference["solver"],"initial_clearances_m":reference["initial_clearances_m"],
           "methods":{n:{"command_vw":r["rollout"]["command_vw"],"rollout_clearance_m":r["rollout"]["minimum_clearance_m"],
                          "safe":r["rollout"]["safe"]} for n,r in reference["results"].items()},
           "not_rerun":True,"different_conditions_not_paired":True}
    table=[]
    for name,r in results.items():
        roll=r["rollout"];c=r["controller"];n=r["native"]
        table.append({"method":name,"status":r["status"],"local_dx_m":c["local_waypoint"][0] if c and c["local_waypoint"] else None,
            "local_dy_m":c["local_waypoint"][1] if c and c["local_waypoint"] else None,
            "v_m_s":c["command_vw"][0] if c else None,"w_rad_s":c["command_vw"][1] if c else None,
            "v_clipped":c["v_clipped"] if c else None,"w_clipped":c["w_clipped"] if c else None,
            "boundary_position_m":r.get("boundary_position_m"),"boundary_tangent_heading_deg":None,
            "trajectory_position_change_rms_m":r.get("trajectory_position_change_rms_m"),"relative_transform_error":None,
            "native_full_clearance_m":n["full"]["obstacle_clearance_m"] if n else None,
            "native_prefix_clearance_m":n["prefix"]["obstacle_clearance_m"] if n else None,
            "rollout_clearance_m":roll["minimum_clearance_m"] if roll else None,"safe":roll["safe"] if roll else None,
            "geometric_overlap":roll["geometric_overlap"] if roll else None,
            "corridor_clearance_m":roll["minimum_corridor_m"] if roll else None,
            "distance_m":roll["distance_m"] if roll else None,"end_pose":json.dumps(roll["end_pose"]) if roll else None})
    with (out/"comparison.csv").open("x") as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator="\n");writer.writeheader();writer.writerows(table)
    for r in results.values():
        if r["rollout"]:r["rollout"].pop("intervals")
    summary={"status":"NOT_RUN_INVALID_INITIAL_HEADING","solve_count":0,"solver":solver,"heading_gate":gate,
        "raw_reproduction":validation,"boundary":boundary.tolist(),"boundary_sim_s":1016/72,"horizon_s":16/72,
        "initial_clearances_m":{k:point_clearance(boundary[:2],lo,hi,.09) for k,(lo,hi) in context.boxes.items()},
        "methods":results,"fixed_goal_B51_reference":fixed,"preserved_run_hashes":len(hashes),
        "limitations":["No Graph convergence, cost, or benefit can be assessed: the original initialization gate rejects this input.",
            "No substitute first yaw, segment skipping, threshold change, weight change, restart, or optimization.",
            "Exact scene geometry offline; no inference/navigation. RAW alone is actual execution.",
            "STOP has no selected waypoint or future trajectory; not reconciliation or a recovery policy."]}
    write_json(out/"summary.json",summary)
    plot(out,context,worlds[51],xy,np.array(e["observation_pose"]),results,gate)
    assert all(sha256_file(run/name)==h for name,h in hashes.items())
    assert all(sha256_file(ROOT/name)==h for name,h in before.items())
    print(json.dumps({"solver":solver,"comparison":table},indent=2))


if __name__=="__main__":
    main()
