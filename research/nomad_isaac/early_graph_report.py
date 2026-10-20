"""Saved-log audit of the two fixed early-obstacle conditions; no inference/solve."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .async_report import rows, stats, validate
from .clearance import corridor_clearance, obstacle_bounds, single_obstacle_config, swept_clearance
from .common import ROOT, local_to_world, original_controller, sha256_file, write_json
from .handoff_audit import path_safety
from .online_graph_factors import local_point
from .oracle_safety_stop import evaluate
from .topomap import candidate_range, select_subgoal
from .topomap_report import validate_map
from .topomap_sudden_report import table


def audit(run, out, graph):
    out.mkdir(exist_ok=False)
    s = json.loads((run/"summary.json").read_text())
    c = s["scenario"]; box = c["dynamic_obstacle"]
    provenance = json.loads((run/"provenance.json").read_text())
    assert provenance["git_status"] == "" and provenance["early_obstacle_mode"] == ("graph" if graph else "raw")
    runtime = validate(run, run.parent/"two_obstacles_01", out/"runtime", actual_command_override=graph)
    manifest, mapcheck = validate_map(Path(c["topomap_manifest"]))
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True)
    pose = np.column_stack([trace[k] for k in ("x_m","y_m","yaw_rad")])
    received, workers, requests, events, controls = [rows(run/n) for n in
        ("received.jsonl","model/inference.jsonl","requests.jsonl","events.jsonl","controller.jsonl")]
    obs = [o for o in rows(run/"observations.jsonl") if "observation_id" in o]
    byid = {e["id"]:e for e in events}
    frames, visible = {}, set()
    for o in obs:
        rgb = np.array(Image.open(run/o["rgb_file"]).convert("RGB"))
        assert hashlib.sha256(rgb.tobytes()).hexdigest() == o["frame_sha256"]
        frames[o["observation_id"]] = rgb
        f = rgb.astype(float)
        mask = (f[:,:,0]>1.5*f[:,:,1]) & (f[:,:,2]>1.5*f[:,:,1]) & (f[:,:,0]>40) & (f[:,:,2]>40)
        active = o["dynamic"]["capture_tick"] >= 792
        assert o["dynamic"]["active"] == active and o["dynamic"]["magenta_pixels"] == int(mask.sum())
        if not active: assert not mask.any()
        if active and mask.sum() >= 20: visible.add(o["observation_id"])
    closest = 0; predictions = []
    both = {**c,"obstacles":[*c["obstacles"],box]}
    for q,r,w in zip(requests,received,workers):
        top=r["topomap"]
        a,b=candidate_range(closest,13)
        assert top==w["topomap"] and top["candidate_ids"]==list(range(a,b+1))
        closest,subgoal,_=select_subgoal(top["distances"],a)
        assert (closest,subgoal)==(top["closest_node"],top["selected_subgoal_id"])
        assert r["goal_sha256"]==manifest["nodes"][subgoal]["rgb_sha256"]
        history=np.stack([frames[i] for i in q["history_observation_ids"]])
        assert hashlib.sha256(history.tobytes()).hexdigest()==w["history_sha256"]
        if visible.intersection(q["history_observation_ids"]):
            with np.load(run/f"model/derived/{r['id']:04d}.npz") as z:
                world=local_to_world(z["metric"][0],r["observation_pose"])
            full,prefix=[path_safety(x,both) for x in (world,world[:3])]
            cmd=list(map(float,original_controller()(r["selected_waypoint_m"])))
            predictions.append({"id":r["id"],"observation_sim_s":r["observation_sim_s"],
                "switch_sim_s":byid.get(r["id"],{}).get("application_sim_s"),"subgoal":subgoal,
                "full_min_m":full["obstacle_clearance_m"],"full_safe":full["safe"],
                "prefix_min_m":prefix["obstacle_clearance_m"],"prefix_safe":prefix["safe"],
                "nominal_v":cmd[0],"nominal_w":cmd[1]})
    table(out/"visible_predictions.csv",predictions)
    activation=rows(run/"dynamic/activation.jsonl")
    gaps=rows(run/"dynamic/clearance.jsonl")
    static=rows(run/"clearance.jsonl")
    error=0.
    for i,a in enumerate(activation):
        assert a["tick"]==i and a["active"]==(i>=792) and a["collision_checked"]==a["active"]
        duration=0 if i==0 else 1/72
        p=pose[max(0,i-1)]
        cmd=[trace["v_m_s"][i],trace["w_rad_s"][i]]
        wall=corridor_clearance(p,pose[i],*cmd,duration,c["corridor"],.09)
        error=max(error,abs(wall-static[i]["corridor_lower_m"]))
        if i>=792:
            dynamic=swept_clearance(pose[i] if i==792 else p,*cmd,0 if i==792 else 1/72,
                                    *obstacle_bounds(single_obstacle_config(c,box)),.09)
            error=max(error,abs(dynamic["lower_m"]-gaps[i-792]["lower_m"]))
            assert dynamic["geometric_overlap"]==gaps[i-792]["geometric_overlap"]
    assert error < 1e-12
    spawn=s["dynamic_obstacle"]["spawn"]
    assert spawn and spawn["tick"]==792 and spawn["obstacle"]==box
    lo,hi=obstacle_bounds(single_obstacle_config(c,box))
    np.testing.assert_allclose(s["frame_and_rgb_check"]["fixed_dynamic_world_aabb"],[[*lo,0],[*hi,.8]],atol=1e-12,rtol=0)
    graph_summary={"requests":0,"solver_calls":0,"valid_results":0,"accepted_actions":0,"moving_actions":0}
    action_rows=[]
    sources=["NOMINAL"]*len(controls)
    if graph:
        decisions=rows(run/"graph_control.jsonl")
        assert len(decisions)==len(controls)
        sources=[d["source"] for d in decisions]
        inputs={int(p.stem.split("_")[-1]):json.loads(p.read_text()) for p in (run/"graph").glob("input_*.json")}
        results={int(p.stem.split("_")[-1]):json.loads(p.read_text()) for p in (run/"graph").glob("result_*.json")}
        assert len(inputs)==s["graph_submitted_requests"]
        assert len({j["fresh_id"] for j in inputs.values()})==len(inputs)
        for j in inputs.values():
            np.testing.assert_array_equal(j["boundary"],pose[j["boundary_tick"]])
            r=received[j["fresh_id"]]
            assert j["observation_pose"]==r["observation_pose"]
            assert j["fresh_received_monotonic_ns"]==r["received_monotonic_ns"]
            assert j["geometry"]==both
            with np.load(run/f"model/derived/{j['fresh_id']:04d}.npz") as z:
                np.testing.assert_array_equal(j["sample0"],z["metric"][0])
            assert (j["submit_monotonic_ns"]-r["received_monotonic_ns"])/1e9 < 1
        for d,control in zip(decisions,controls):
            tick=d["tick"];np.testing.assert_array_equal(d["pose"],pose[tick])
            assert d["nominal_vw"]==[control["v_m_s"],control["w_rad_s"]]
            assert d["applied_vw"]==[control["applied_v_m_s"],control["applied_w_rad_s"]]
            if tick>=792:
                check=evaluate(c,pose[tick],d["nominal_vw"],box)
                assert abs(check["minimum_clearance_lower_m"]-d["nominal_check"]["minimum_clearance_lower_m"])<1e-12
            if d["source"] in ("GRAPH_WAIT","SAFETY_STOP","GRAPH_SAFETY_STOP"):
                assert d["applied_vw"]==[0.,0.]
            if d["source"]=="GRAPH":
                j=inputs[d["graph_id"]];r=results[d["graph_id"]]
                assert r["status"]=="CONVERGED"
                world=np.array(r["optimized_world_poses"])
                point=local_point(world[2,:2],np.array(j["boundary"]))
                np.testing.assert_allclose(point,r["corrected_B_local_waypoint"],atol=1e-12,rtol=0)
                np.testing.assert_allclose(original_controller()(point),d["applied_vw"],atol=1e-12,rtol=0)
                assert evaluate(c,pose[tick],d["applied_vw"],box)["safe"]
            if d.get("result",{}).get("accepted"):
                j=inputs[d["graph_id"]];r=results[d["graph_id"]]
                assert d["result"]["valid_B"] and d["result"]["valid_geometry"]
                np.testing.assert_allclose(pose[tick],j["boundary"],atol=1e-9,rtol=0)
                matching=[a for a in decisions if a["source"]=="GRAPH" and a["graph_id"]==j["graph_id"]]
                ticks=[a["tick"] for a in matching]
                intervals=[i for a in ticks for i in range(a+1,min(a+9,len(trace)))]
                assert intervals and max(intervals)-tick<=16
                distance=float(np.sum(np.abs(trace["v_m_s"][intervals]))/72)
                yaw=float(np.sum(trace["w_rad_s"][intervals])/72)
                end=max(intervals)
                # A new RGB can include a Graph-shifted pose even before the entire action ends.
                shifted_obs=[o for o in obs if tick/72 < o["observation_sim_s"] and
                             np.max(np.abs(np.array(o["observation_pose"])-np.array(j["boundary"])))>1e-8]
                first_oid=shifted_obs[0]["observation_id"] if shifted_obs else None
                feedback=next((q["id"] for q in requests if first_oid in q["history_observation_ids"]),None)
                source_input_nominal=list(map(float,original_controller()(j["sample0"][2])))
                action_rows.append({"graph_id":j["graph_id"],"fresh_id":j["fresh_id"],"B_tick":j["boundary_tick"],
                    "application_tick":tick,"application_sim_s":tick/72,"solve_wall_s":(r["solve_end_monotonic_ns"]-r["solve_start_monotonic_ns"])/1e9,
                    "wait_wall_s":d["result"]["wait_wall_s"],"input_age_s":d["action"]["original_input_age_at_application_s"],
                    "receive_age_s":d["action"]["original_receive_age_at_application_s"],
                    "nominal_v":source_input_nominal[0],"nominal_w":source_input_nominal[1],
                    "graph_v":d["applied_vw"][0],"graph_w":d["applied_vw"][1],
                    "original_waypoint":j["sample0"][2],"corrected_waypoint":r["corrected_B_local_waypoint"],
                    "selected_world_displacement_m":float(np.linalg.norm(world[2,:2]-np.array(r["original_world_xy"])[2])),
                    "executed_distance_m":distance,"executed_yaw_rad":yaw,"end_pose":pose[end].tolist(),
                    "actual_clearance_m":min(min(static[i]["lower_m"],gaps[i-792]["lower_m"]) for i in intervals),
                    "subsequent_RGB_at_shifted_pose":len(shifted_obs)>0,
                    "first_subsequent_RGB_id":first_oid,"subsequent_inference_request_using_RGB":feedback})
        table(out/"graph_actions.csv",action_rows)
        # Single outstanding request and fixed pose during the actual stop-and-plan window.
        ordered=[inputs[key] for key in sorted(inputs)]
        for a,b in zip(ordered[:-1],ordered[1:]):
            assert b["submit_monotonic_ns"]>=results[a["graph_id"]]["solve_end_monotonic_ns"]
        for j in ordered:
            consumption=next((d for d in decisions if d.get("result",{}).get("graph_id")==j["graph_id"]),None)
            end_tick=consumption["tick"] if consumption else len(trace)-1
            np.testing.assert_allclose(pose[j["boundary_tick"]:end_tick+1],np.tile(j["boundary"],(end_tick-j["boundary_tick"]+1,1)),atol=1e-12,rtol=0)
        graph_summary={"requests":len(inputs),"solver_calls":sum(r["solver_called"] for r in results.values()),
            "result_statuses":dict(Counter(r["status"] for r in results.values())),
            "converged_results":sum(r["status"]=="CONVERGED" for r in results.values()),
            "valid_results":sum(d.get("result",{}).get("accepted",False) for d in decisions),
            "accepted_actions":len(action_rows),"moving_actions":sum(a["executed_distance_m"]>0 or a["executed_yaw_rad"]!=0 for a in action_rows),
            "graph_distance_m":sum(a["executed_distance_m"] for a in action_rows),
            "graph_solve_wall_s":stats([(r["solve_end_monotonic_ns"]-r["solve_start_monotonic_ns"])/1e9 for r in results.values() if r["solver_called"]]),
            "wait_wall_s":stats([d["result"]["wait_wall_s"] for d in decisions if "result" in d]),
            "input_age_at_application_s":stats([a["input_age_s"] for a in action_rows]),
            "accepted_after_original_timeout":sum(a["receive_age_s"]>=1 for a in action_rows),
            "pending_result_unapplied_at_end":[key for key in results if not any(d.get("result",{}).get("graph_id")==key for d in decisions)],
            "action_ids_with_followup_RGB":[a["graph_id"] for a in action_rows if a["subsequent_RGB_at_shifted_pose"]],
            "action_ids_with_followup_inference":[a["graph_id"] for a in action_rows if a["subsequent_inference_request_using_RGB"] is not None]}
    durations=[min(8,len(trace)-1-i*8)/72 for i in range(len(controls))]
    bysource={key:sum(d for d,sr in zip(durations,sources) if sr==key) for key in set(sources)}
    stopped=float(np.sum((trace["v_m_s"][1:]==0)&(trace["w_rad_s"][1:]==0))/72)
    evals=[s["obstacle_evaluation"],s["dynamic_obstacle"]["evaluation"]]
    safe=all(e["safety_margin_met"] and e["corridor_containment_certified"] for e in evals)
    collision=any(e["geometric_overlap"] for e in evals)
    classification="SAFE_GOAL_SUCCESS" if safe and s["goal_entry"] else "SAFETY_FAILURE" if not safe else "SAFE_BUT_STUCK" if graph and stopped>1 else "SAFE_GOAL_FAILURE"
    first_failure=None
    for i in range(792,len(trace)):
        if min(static[i]["lower_m"],gaps[i-792]["lower_m"])<.02 or static[i]["corridor_lower_m"]<=0:
            ci=(i-1)//8
            first_failure={"tick":i,"simulation_time_s":i/72,"pose":pose[i].tolist(),
                "nominal_waypoint_id":int(trace["incoming_waypoint_id"][i]),"actual_source":sources[ci],
                "command_vw":[trace["v_m_s"][i],trace["w_rad_s"][i]],
                "minimum_clearance_m":min(static[i]["lower_m"],gaps[i-792]["lower_m"])}
            break
    first_visible=next((o for o in obs if o["observation_id"] in visible),None)
    result={"classification":classification,"source_run":str(run),"execution_git_sha":provenance["git_sha"],
        "navigation":{k:s[k] for k in ("goal_entry","termination_reason","simulation_duration_s","minimum_goal_distance_m","final_pose","distance_travelled_m")},
        "spawn":spawn,"first_visible":{k:first_visible[k] for k in ("observation_id","observation_sim_s","observation_pose")} if first_visible else None,
        "first_visible_fresh":predictions[0] if predictions else None,
        "visible_native_predictions":{"n":len(predictions),"full_safe":sum(p["full_safe"] for p in predictions),"prefix_safe":sum(p["prefix_safe"] for p in predictions)},
        "safety":{"static":s["obstacle_evaluation"],"dynamic":s["dynamic_obstacle"]["evaluation"],"safe":safe,"collision":collision,"first_margin_or_corridor_failure":first_failure},
        "stop_time_sim_s":stopped,"execution_source_duration_sim_s":bysource,"graph":graph_summary,
        "runtime":{k:runtime[k] for k in ("async_reproduction","warm_inference_ms","pacing","requests","received","switches","timeout","busy_observation_skips","missed_capture_slots")},
        "validation":{"pose_error":runtime["validation"]["max_pose_integration_error"],"clearance_error":error,"Topomap":mapcheck,
            "raw_semantics_and_original_nominal_PD":"PASS","worker_history_and_visible_RGB":"PASS","graph_execution_and_followup_pose":"PASS" if action_rows else "NOT_EXERCISED"}}
    write_json(out/"summary.json",result)
    files=[p for p in run.rglob("*") if p.is_file() and p.suffix in (".json",".jsonl",".csv",".npz",".png",".usda") and
           p.parent.name in (run.name,"graph","model","raw","derived","observations","dynamic")]
    write_json(out/"input_hashes.json",{str(p.relative_to(run)):sha256_file(p) for p in files})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    a.out.mkdir(exist_ok=False)
    base=ROOT.parent/"artifacts/isaac6"
    reports={name:audit(base/run,a.out/name,name=="EARLY-GRAPH") for name,run in
             (("EARLY-RAW","early_raw_01"),("EARLY-GRAPH","early_graph_01"))}
    write_json(a.out/"summary.json",reports)
    plot(reports,a.out)
    print(json.dumps({k:{"classification":v["classification"],"navigation":v["navigation"],"graph":v["graph"]} for k,v in reports.items()}))


def plot(reports,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle
    plt.rcParams.update({"svg.fonttype":"none","svg.hashsalt":"early-graph","path.simplify":False})
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharex=True,sharey=True)
    for ax,(name,r) in zip(axes,reports.items()):
        run=Path(r["source_run"]);c=json.loads((run/"scenario.json").read_text())
        t=np.genfromtxt(run/"agent_trajectory.csv",delimiter=",",names=True)
        for box in [*c["obstacles"],c["dynamic_obstacle"]]:
            lo,hi=obstacle_bounds(single_obstacle_config(c,box))
            ax.add_patch(Rectangle(lo,*(hi-lo),fc="#cd8bbe" if box["id"]=="DynamicObstacle" else "#9fbd97",alpha=.65))
        ax.plot(t["x_m"],t["y_m"],c="#215dac",lw=2,label="Actual executed path")
        if name=="EARLY-GRAPH":
            decisions=rows(run/"graph_control.jsonl")
            first=True
            for d in decisions:
                if d["source"]=="GRAPH":
                    sl=slice(d["tick"],min(d["tick"]+9,len(t)))
                    ax.plot(t["x_m"][sl],t["y_m"][sl],c="#e15b23",lw=4,label="Actual Graph-command execution" if first else None)
                    first=False
        ax.scatter(t["x_m"][792],t["y_m"][792],marker="^",c="#822272",label="Spawn pose",zorder=5)
        ax.scatter(t["x_m"][-1],t["y_m"][-1],marker="x",c="#bb3344",label="Final pose",zorder=6)
        ax.add_patch(Circle((t["x_m"][-1],t["y_m"][-1]),.09,fill=False,ec="#bb3344"))
        ax.add_patch(Circle(c["goal_pose"][:2],.3,fc="#f2dfab",alpha=.5))
        ax.scatter(*c["goal_pose"][:2],marker="*",s=120,c="#b27b00",label="Goal")
        for y in (-1.5,1.5):ax.axhline(y,c="#777777",lw=1)
        ax.set_aspect("equal");ax.set(xlim=(-.2,4.9),ylim=(-1.6,1.6),xlabel="World X (m)",ylabel="World Y (m)")
        ax.set_title(f"{name} | {r['classification']}\nEnd {r['navigation']['simulation_duration_s']:.3f} s; Graph actions {r['graph']['accepted_actions']}",fontsize=10)
        ax.grid(alpha=.15);ax.legend(loc="lower left",fontsize=7)
    fig.suptitle("11 s fixed obstacle appearance | actual closed-loop executions",fontsize=13)
    fig.tight_layout()
    fig.savefig(out/"navigation_comparison.png",dpi=170)
    svg=out/"navigation_comparison.svg";fig.savefig(svg,metadata={"Date":None})
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)


if __name__=="__main__":main()
