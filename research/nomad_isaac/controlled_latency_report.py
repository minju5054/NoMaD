"""Offline B0/B_delay audit of one controlled result-delivery hold."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from .common import ROOT, local_to_world, sha256_file, write_json
from .async_report import rows, validate, wrapped
from .async_handoff_audit import motion
from .handoff_audit import correspondence, boundary_entries, path_safety, classify
from .clearance import configured_obstacles, obstacle_bounds, single_obstacle_config, corridor_clearance


def first_control_after(control, wall_ns):
    return next((c for c in control if c["monotonic_ns"] >= wall_ns), None)


def draw_comparison(details, config, pose, start, stop, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle, Circle
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "controlled-latency", "font.size": 10})
    old, fresh = (np.array(details[k+"_world_xy_m"]) for k in ("old", "fresh"))
    b0, bd = (np.array(details[k]["pose"]) for k in ("B0", "B_delay"))
    all_xy = np.vstack([old, fresh, b0[:2], bd[:2]])
    xmin, xmax = all_xy[:,0].min()-.18, all_xy[:,0].max()+.22
    ymin, ymax = min(all_xy[:,1].min()-.22, -.15), max(all_xy[:,1].max()+.23, .15)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.7))
    for ax, name in zip(axes, ("B0", "B_delay")):
        boundary = details[name]; b = np.array(boundary["pose"])
        for box in configured_obstacles(config):
            lo, hi = obstacle_bounds(single_obstacle_config(config, box))
            ax.add_patch(Rectangle(lo, *(hi-lo), color="#badfb0", ec="#428342", alpha=.8))
        ax.plot(*pose[:,:2].T, ":", color="#b9b9b9", lw=1, label="Full recorded route")
        ax.plot(*pose[start:stop+1,:2].T, color="#087f7f", lw=4, label="Actual OLD: B0 to B_delay")
        for role, p, color in (("old", old, "#cd7d12"), ("fresh", fresh, "#2165d6")):
            ax.plot(*p.T, "o-", color=color, ms=4, lw=1.8)
            ax.scatter(*p[2], marker="*", s=140, c=color, edgecolor="white", zorder=5)
            obs = details[role+"_observation_pose"]
            ax.scatter(*obs[:2], marker="s", facecolor="white", edgecolor=color, s=36, zorder=6)
            ax.annotate("", xy=np.array(obs[:2])+.06*np.array([np.cos(obs[2]),np.sin(obs[2])]),
                        xytext=obs[:2], arrowprops={"arrowstyle":"->","color":color})
        ax.scatter(*b0[:2], marker="x", color="black", s=55, zorder=8)
        ax.scatter(*bd[:2], marker="+", color="#ad287f", s=85, zorder=8)
        ax.add_patch(Circle(b[:2], config["agent_radius_m"], fill=False, color="black", ls="--"))
        ax.annotate("", xy=b[:2]+.08*np.array([np.cos(b[2]),np.sin(b[2])]), xytext=b[:2],
                    arrowprops={"arrowstyle":"->","color":"black"}, zorder=8)
        entry = boundary["entry"].get("chosen")
        if entry:
            e=np.array(entry["xy_m"])
            ax.plot(*np.vstack([b[:2], e]).T, "--", color="#a02aa4", lw=2)
            ax.scatter(*e, marker="D", color="#a02aa4", s=40, zorder=9)
            caption=f"Entry distance {entry['distance_m']*100:.2f} cm | connector clearance {entry['obstacle_clearance_m']*100:.2f} cm"
        else:
            caption="No valid spatial entry"
        ax.set(xlim=(xmin,xmax), ylim=(ymin,ymax), xlabel="World x (m)", ylabel="World y (m)")
        ax.set_aspect("equal", adjustable="box"); ax.grid(alpha=.18)
        ax.set_title(f"{name}: t = {boundary['sim_s']:.3f} s\n{boundary['class']}", fontsize=12, pad=13)
        ax.text(0, -.25, caption, transform=ax.transAxes, fontsize=9.5)
    handles=[Line2D([],[],color="#cd7d12",marker="o",label="OLD (observation-anchored)"),
             Line2D([],[],color="#2165d6",marker="o",label="FRESH (same path in both panels)"),
             Line2D([],[],color="#087f7f",lw=4,label="Actual OLD between boundaries"),
             Line2D([],[],color="black",marker="x",ls="none",label="B0: recorded OLD pose"),
             Line2D([],[],color="#ad287f",marker="+",ls="none",label="B_delay: actual FRESH switch"),
             Line2D([],[],color="#a02aa4",ls="--",marker="D",label="Unexecuted connector / entry")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5,.075), ncol=3, frameon=False, fontsize=9)
    fig.suptitle(f"One delayed handoff: OLD {details['old_id']} → FRESH {details['fresh_id']}", fontsize=17, y=.98)
    fig.text(.05,.91,"Same saved predictions and observation anchors; B0 is not a simulated no-delay rollout.", fontsize=10)
    fig.text(.05,.025,"Stars: selected index 2. Squares/arrows: observation poses. Circle: 9 cm footprint. Green: obstacle (cropped zoom).\n"
             "Obstacle 2 extends to the left wall at world y = 1.5 m. Connectors are offline diagnostics, not executed PD paths.", fontsize=9)
    fig.subplots_adjust(top=.80,bottom=.29,wspace=.24)
    for ext in ("png","svg"):
        fig.savefig(output/f"boundary_comparison.{ext}",dpi=180,metadata={"Date":None} if ext=="svg" else None)
    plt.close(fig)
    svg=output/"boundary_comparison.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")


def analyze(run, baseline, output):
    output.mkdir(parents=True, exist_ok=False)
    protocol=json.loads(Path(__file__).with_name("controlled_latency_protocol.json").read_text())
    geometric=json.loads(Path(__file__).with_name("async_handoff_protocol.json").read_text())
    config=json.loads((run/"scenario.json").read_text())
    assert config==json.loads((baseline/"scenario.json").read_text())
    assert json.loads((run/"delivery_delay_protocol.json").read_text())==protocol
    preservation=json.loads((baseline.parent/"controlled_latency_preservation_01.json").read_text())["sha256"]
    assert all(sha256_file(baseline/n)==h for n,h in preservation.items())
    input_paths=sorted(p for p in run.iterdir() if p.suffix in (".json", ".jsonl", ".csv", ".png", ".usd", ".usda"))
    input_paths+=sorted((run/"model").glob("*.json*"))+sorted((run/"model/raw").glob("*.npz"))+sorted((run/"model/derived").glob("*.npz"))
    hashes={str(p.relative_to(run)):sha256_file(p) for p in input_paths}
    provenance=json.loads((run/"provenance.json").read_text())
    assert provenance["git_status"]=="" and provenance["controlled_delivery_delay"]
    for name,digest in provenance["source_sha256"].items():
        historical=subprocess.check_output(["git","show",f"{provenance['git_sha']}:{name}"],cwd=ROOT)
        assert hashlib.sha256(historical).hexdigest()==digest
    protected=["research/nomad_isaac/worker.py", "research/nomad_isaac/common.py", "research/nomad_isaac/clearance.py",
        "research/nomad_isaac/two_obstacles_wide_wall_scenario.json", "research/nomad_preflight/native.py",
        "deployment/src/pd_controller.py", "deployment/src/navigate.py", "deployment/src/ros_data.py",
        "research/nomad_isaac/handoff_audit.py", "research/nomad_isaac/async_handoff_protocol.json"]
    for name in protected:
        original=subprocess.check_output(["git","show",f"{protocol['base_commit']}:{name}"],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==sha256_file(ROOT/name)
    environment=json.loads((run/"model/environment.json").read_text())
    base_env=json.loads((baseline/"model/environment.json").read_text())
    assert environment["checkpoint_sha256"]==base_env["checkpoint_sha256"]
    runtime=validate(run, baseline.parent/"two_obstacles_01", output/"runtime_validation")
    received, events, control, requests, clearance=(rows(run/n) for n in
        ["received.jsonl","events.jsonl","controller.jsonl","requests.jsonl","clearance.jsonl"])
    with (run/"agent_trajectory.csv").open() as f: records=list(csv.DictReader(f))
    pose=np.array([[float(r[k]) for k in ("x_m","y_m","yaw_rad")] for r in records])
    wall=np.array([int(r["monotonic_ns"]) for r in records],dtype=np.int64)
    sim=np.array([float(r["simulation_time_s"]) for r in records])
    trace={"pose":pose,"wall":wall,"dt":1/config["integration_hz"],
           "command":np.array([[float(r[k]) for k in ("v_m_s","w_rad_s")] for r in records]),
           "id":np.array([int(r["incoming_waypoint_id"]) for r in records]),
           "valid":np.array([r["incoming_command_valid"]=="True" for r in records])}
    def tick(t):
        i=round(t*config["integration_hz"])
        assert abs(sim[i]-t)<1e-10
        return i
    for r in received:
        chain=[r[k] for k in ("inference_end_monotonic_ns","host_output_ready_monotonic_ns",
            "persistence_end_monotonic_ns","packet_received_monotonic_ns","release_deadline_monotonic_ns",
            "release_monotonic_ns","latched_monotonic_ns")]
        assert np.all(np.diff(np.array(chain,dtype=np.int64))>=0)
        assert r["release_deadline_monotonic_ns"]-r["packet_received_monotonic_ns"]==round(r["additional_delivery_delay_s"]*1e9)
        assert r["received_monotonic_ns"]==r["release_monotonic_ns"]
        p=tick(r["packet_received_sim_s"])
        np.testing.assert_allclose(pose[p],r["agent_pose_at_packet_receive"],atol=1e-12,rtol=0)
        assert wall[p]==r["packet_pose_sample_monotonic_ns"]
    lo,hi=protocol["observation_world_x_inclusive_m"]
    eligible=[q for q in requests if lo<=q["observation_pose"][0]<=hi and q["old_valid_at_observation"] and q["old_id_at_observation"]>=0]
    triggered=[r for r in received if r["delivery_delay_triggered"]]
    assert [r["id"] for r in triggered]==[q["id"] for q in eligible[:1]]
    assert sum(r["additional_delivery_delay_s"]>0 for r in received)==len(triggered)<=1
    base_summary=json.loads((baseline/"summary.json").read_text())
    current=json.loads((run/"summary.json").read_text())
    report={"source_run":str(run),"baseline_run":str(baseline),"execution_commit":provenance["git_sha"],
        "protocol":protocol,"trigger_status":"TRIGGERED" if triggered else "NOT_TRIGGERED",
        "classification":"INSUFFICIENT_EVIDENCE","verdict":"INSUFFICIENT_EVIDENCE",
        "runtime":{k:runtime[k] for k in ("async_reproduction","real_time_pacing_pass","inference_clock_mapping_pass",
            "warm_inference_ms","requests","switches","timeout","pacing","busy_observation_skips","missed_capture_slots")},
        "navigation":{role:{k:s[k] for k in ("goal_entry","termination_reason","simulation_duration_s",
                "minimum_goal_distance_m","obstacle_evaluation")} for role,s in (("baseline",base_summary),("delayed",current))},
        "validation":{"baseline_hashes_unchanged":len(preservation),"original_sources_unchanged":protected,
            "scenario_unchanged":True,"checkpoint_unchanged":True,"model_controller_pose_output_validation":"PASS",
            "first_eligible_request_triggered_once":True,"physical_packet_release_clocks_verified":True},
        "limitations":["One fixed-goal run; RGB and diffusion sampling differences prevent whole-run causal attribution",
            "B0 is an actual OLD pose at a counterfactual delivery tick, not a no-delay FRESH rollout",
            "Same predictions stay observation-anchored; boundary-relative overlap may change between B0 and B_delay",
            "Finite automatic entry/connector diagnostics do not establish Graph performance or superiority"]}
    details=None; table=[]
    if triggered:
        r=triggered[0]; j=r["id"]
        packet,release=r["packet_received_monotonic_ns"],r["release_monotonic_ns"]
        prior=[e for e in events if e["application_monotonic_ns"]<packet]
        old=prior[-1] if prior else None
        actual=next((e for e in events if e["id"]==j),None)
        c0=first_control_after(control,packet)
        report["trigger"]={"fresh_id":j,"old_id":old["id"] if old else None,
            "observation_pose":r["observation_pose"],"t_obs_sim_s":r["observation_sim_s"],
            "clocks_host_monotonic_ns":{k:r[k] for k in ("observation_monotonic_ns","ready_monotonic_ns",
                "packet_received_monotonic_ns","release_deadline_monotonic_ns","release_monotonic_ns")},
            "t_switch_monotonic_ns":actual["application_monotonic_ns"] if actual else None,
            "configured_delay_s":r["additional_delivery_delay_s"],"measured_packet_to_release_s":(release-packet)/1e9,
            "deadline_overshoot_s":(release-r["release_deadline_monotonic_ns"])/1e9,"gpu_inference_ms":r["inference_ms"],
            "observation_to_ready_s":(r["ready_monotonic_ns"]-r["observation_monotonic_ns"])/1e9,
            "busy_skips_during_hold":sum(o.get("status")=="busy_history_only" and packet<=o.get("capture_end_monotonic_ns",0)<=release for o in rows(run/"observations.jsonl")),
            "timeout_refreshes_during_hold":sum(c["status"]=="expired" and packet<=c["monotonic_ns"]<=release for c in control),
            "actually_applied":actual is not None}

        def executed_safety(start,end):
            if end<=start: return {"interval_count":0,"safe":None}
            boxes={box["id"]:min(clearance[i]["obstacles"][box["id"]]["lower_m"] for i in range(start+1,end+1))
                   for box in configured_obstacles(config)}
            gaps=[]
            for i in range(start+1,end+1):
                gap=corridor_clearance(pose[i-1],pose[i],*trace["command"][i],trace["dt"],config["corridor"],config["agent_radius_m"])
                assert abs(gap-clearance[i]["corridor_lower_m"])<1e-10
                gaps.append(gap)
            minimum=min(boxes.values()); corridor=min(gaps)
            return {"interval_count":end-start,"start_sim_s":sim[start],"end_sim_s":sim[end],"obstacles":boxes,
                    "minimum_clearance_m":minimum,"corridor_clearance_m":corridor,
                    "safe":minimum>=config["required_clearance_m"] and corridor>0,
                    "incoming_waypoint_ids":sorted(set(map(int,trace["id"][start+1:end+1]))),
                    "invalid_intervals":int(np.sum(~trace["valid"][start+1:end+1]))}

        stop=tick(actual["application_sim_s"]) if actual else len(pose)-1
        begin=int(np.clip(np.searchsorted(wall,packet,side="right")-1,0,len(pose)-1))
        old_safety=executed_safety(begin,stop)
        report["old_execution_during_hold_through_switch"]=old_safety
        if actual:
            next_event=next((e for e in events if e["application_monotonic_ns"]>actual["application_monotonic_ns"]),None)
            after=tick(next_event["application_sim_s"]) if next_event else len(pose)-1
            report["fresh_actual_execution_to_next_switch"]=executed_safety(stop,after)
        if old is not None and actual is not None and c0 is not None:
            k=old["id"]; start=tick(c0["simulation_time_s"])
            assert start<=stop
            details={"old_id":k,"fresh_id":j,"old_observation_pose":old["observation_pose"],"fresh_observation_pose":r["observation_pose"]}
            paths={}
            for role,record in (("old",old),("fresh",r)):
                with np.load(run/f"model/derived/{record['id']:04d}.npz",allow_pickle=False) as data:
                    world=local_to_world(data["metric"][0],record["observation_pose"])
                details[role+"_world_xy_m"]=world.tolist()
                origin=np.vstack([record["observation_pose"][:2],world])
                paths[role]={"native_full":path_safety(world,config),"native_prefix":path_safety(world[:3],config),
                             "origin_full":path_safety(origin,config),"origin_prefix":path_safety(origin[:4],config)}
            old_world,fresh_world=(np.array(details[k+"_world_xy_m"]) for k in ("old","fresh"))
            for name,index,control_ns in (("B0",start,c0["monotonic_ns"]),("B_delay",stop,actual["application_monotonic_ns"])):
                b=pose[index]
                overlap=correspondence(old_world,fresh_world,b,geometric)
                entry=boundary_entries(fresh_world,b,config,geometric)
                label=classify(paths["fresh"]["native_full"],overlap,entry,geometric)
                details[name]={"pose":b.tolist(),"sim_s":sim[index],"control_monotonic_ns":control_ns,
                    "pose_monotonic_ns":int(wall[index]),"overlap":overlap,"entry":entry,"class":label}
                near=entry.get("nearest",{});chosen=entry.get("chosen",{})
                table.append({"boundary":name,"fresh_id":j,"old_id":k,"sim_s":sim[index],"x_m":b[0],"y_m":b[1],"yaw_rad":b[2],
                    "class":label,"overlap_valid":overlap["valid"],"position_rmse_m":overlap.get("progress_spatial_rmse_m"),
                    "heading_rms_deg":overlap.get("progress_heading_rms_deg"),"nearest_entry_distance_m":near.get("distance_m"),
                    "nearest_tangent_difference_deg":near.get("boundary_tangent_deg"),"nearest_connector_bearing_deg":near.get("boundary_connector_deg"),
                    "chosen_entry_distance_m":chosen.get("distance_m"),"connector_clearance_m":chosen.get("obstacle_clearance_m"),
                    "connector_corridor_clearance_m":chosen.get("corridor_clearance_m"),"safe_entry_count":entry.get("safe_count",0)})
            details["paths"]=paths
            report["boundaries"]={name:details[name] for name in ("B0","B_delay")}
            report["paths"]=paths
            report["additional_old_motion_B0_to_B_delay"]=motion(trace,start,stop,waypoint_id=k)
            report["additional_old_motion_B0_to_B_delay"].update({"world_pose_delta":[*map(float,pose[stop,:2]-pose[start,:2]),float(wrapped(pose[stop,2]-pose[start,2]))],
                "net_translation_m":float(np.linalg.norm(pose[stop,:2]-pose[start,:2])),
                "control_tick_delay_increase_wall_s":(actual["application_monotonic_ns"]-c0["monotonic_ns"])/1e9,
                "control_tick_delay_increase_sim_s":sim[stop]-sim[start]})
            report["old_B0_to_B_delay_safety"]=executed_safety(start,stop)
            report["trigger"]["observation_to_switch_s"]=(actual["application_monotonic_ns"]-r["observation_monotonic_ns"])/1e9
            valid_b0=c0["valid"] and c0["waypoint_id"]==k and c0["latest_received_id"]==k
            report["validation"]["B0_has_valid_old"]=bool(valid_b0)
            np.testing.assert_allclose(pose[stop],actual["agent_pose_at_switch"],atol=1e-12,rtol=0)
            first=first_control_after(control,release)
            report["validation"]["release_to_next_controller_tick_exact"]=bool(first and first["monotonic_ns"]==actual["application_monotonic_ns"])
            report["classification"]=details["B_delay"]["class"] if valid_b0 else "INSUFFICIENT_EVIDENCE"
            if not old_safety["safe"]: report["classification"]="OLD_EXECUTION_RISK"
            verified=runtime["real_time_pacing_pass"] and runtime["inference_clock_mapping_pass"] and valid_b0 and report["validation"]["release_to_next_controller_tick_exact"]
            report["controlled_delivery_reproduction"]="PASS" if verified and report["additional_old_motion_B0_to_B_delay"]["distance_m"]>0 else "FAIL"
            report["verdict"]=("GEOMETRIC_CANDIDATE_FOUND" if report["classification"]=="POTENTIAL_RECONCILIATION_CASE" else
                "INSUFFICIENT_EVIDENCE" if report["classification"]=="INSUFFICIENT_EVIDENCE" or not verified else "NO_QUALIFIED_CANDIDATE")
            draw_comparison(details,config,pose,start,stop,output)
        elif old_safety.get("safe") is False:
            report["classification"]="OLD_EXECUTION_RISK"
    assert all(sha256_file(run/n)==h for n,h in hashes.items())
    assert all(sha256_file(baseline/n)==h for n,h in preservation.items())
    report["validation"]["new_run_input_hashes_unchanged"]=len(hashes)
    write_json(output/"summary.json",report)
    write_json(output/"input_hashes.json",hashes)
    write_json(output/"pair_details.json",details)
    with (output/"boundaries.csv").open("x") as f:
        if table:
            writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    print(json.dumps({k:report[k] for k in ("trigger_status","classification","verdict")}))
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();analyze(args.run.resolve(),args.baseline.resolve(),args.output.resolve())
