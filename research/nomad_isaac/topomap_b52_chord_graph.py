"""One B52 solve with only the first tangent changed to a frozen longer chord."""
import argparse
import csv
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import scipy
from scipy.optimize import least_squares

from .common import ROOT, local_to_world, sha256_file, write_json
from .clearance import point_clearance
from .minimal_se2_graph import (Experiment, derived_headings, local_point, minimal_algebra_checks,
                               rigid_alignment, validate_actual_after_solve, wrap)
from .topomap_b52_graph import command_detail


def chord_headings(xy, k):
    heading, lengths = derived_headings(xy)
    chord = xy[k] - xy[0]
    chord_length = float(np.linalg.norm(chord))
    if chord_length == 0:
        raise ValueError("Undefined first chord tangent: zero X0->Xk chord")
    # Only the first heading changes. Wrapping inside factors handles the yaw chart.
    heading[0] = np.arctan2(chord[1], chord[0])
    return heading, lengths, chord_length


class ChordExperiment(Experiment):
    def __init__(self, initial, boundary, config, protocol, k):
        super().__init__(initial, boundary, config, protocol)
        self.k = k

    def groups(self, poses):
        group = super().groups(poses)
        tangent, _, _ = chord_headings(poses[:, :2], self.k)
        group["heading_tangent"][0] = wrap(poses[0, 2] - tangent[0]) / np.radians(self.p["tangent_consistency_sigma_deg"])
        return group

    def evaluate(self, name, poses, raw_point):
        result = super().evaluate(name, poses, raw_point)
        tangent, lengths, chord_length = chord_headings(poses[:, :2], self.k)
        valid = np.r_[lengths >= self.p["minimum_heading_segment_m"], lengths[-1] >= self.p["minimum_heading_segment_m"]]
        valid[0] = chord_length >= self.p["minimum_heading_segment_m"]
        delta = np.degrees(wrap(tangent - self.initial[:, 2]))
        result.update(first_tangent_k=self.k, first_tangent_chord_m=chord_length,
            heading_valid=valid.tolist(), adjacent_segment_minimum_met=(lengths >= .02).tolist(),
            boundary_tangent_heading_deg=float(abs(np.degrees(wrap(tangent[0]-self.boundary[2])))) if valid[0] else None,
            tangent_heading_change_rms_deg=float(np.sqrt(np.mean(delta[valid]**2))) if valid.any() else None,
            tangent_pose_disagreement_max_deg=float(np.max(abs(np.degrees(wrap(tangent[valid]-poses[valid,2]))))) if valid.any() else None)
        result["controller"] = command_detail(np.array(result["controller_local_waypoint"]))
        np.testing.assert_array_equal(result["controller"]["command_vw"], result["rollout"]["command_vw"])
        return result


def read_before_boundary(run, plan, protocol):
    with (run/"events.jsonl").open() as stream:
        for line in stream:
            event = json.loads(line)
            if event["id"] == plan["fresh_id"]:
                break
        else:
            raise ValueError("FRESH52 event missing")
    assert event["observation_sim_s"] == plan["observation_tick"]/72
    assert event["application_sim_s"] == plan["boundary_tick"]/72
    boundary = np.array(event["agent_pose_at_switch"])
    with (run/"agent_trajectory.csv").open() as stream:
        for row in csv.DictReader(stream):
            if int(row["tick"]) == plan["boundary_tick"]:
                np.testing.assert_array_equal(boundary, [float(row[k]) for k in ("x_m","y_m","yaw_rad")])
                break
        else:
            raise ValueError("B52 pose missing")
    np.testing.assert_allclose(boundary,[2.294383156,.399014947,-.636309015],atol=1e-9,rtol=0)
    config = json.loads((run/"scenario.json").read_text())
    spawn = json.loads((run/"dynamic/spawn.json").read_text())
    assert spawn["tick"] < plan["boundary_tick"]
    config["obstacles"] = [*config["obstacles"],spawn["obstacle"]]
    assert config["agent_radius_m"] == protocol["radius_m"] == .09
    assert config["required_clearance_m"] == protocol["required_clearance_m"] == .02
    assert config["integration_hz"] == protocol["integration_hz"] == 72
    with np.load(run/"model/derived/0052.npz",allow_pickle=False) as data:
        assert data["metric"].shape == (8,8,2)
        local = data["metric"][0].astype(float)
    assert np.isfinite(local).all()
    world = local_to_world(local,event["observation_pose"])
    np.testing.assert_array_equal(local[2],event["selected_waypoint_m"])
    return event,boundary,config,local,world


def plot_comparison(out, exp, observation, results):
    # Reuses original two-panel graph layout, obstacle contours and rollout footprints.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    plt.rcParams.update({"svg.fonttype":"none","svg.hashsalt":"topomap-b52-chord","path.simplify":False})
    colors={"RAW":"#d1495b","B-LOCAL":"#2875b6","RIGID":"#d68b00","GRAPH":"#008b78","STOP":"#46525f"}
    fig,axes=plt.subplots(1,2,figsize=(13.5,6.5),gridspec_kw={"width_ratios":[1.3,1]})
    future=np.concatenate([np.array(r["world_poses"])[:,:2] for r in results.values() if r.get("world_poses")])
    traces=np.concatenate([np.array(r["rollout"]["poses"])[:,:2] for r in results.values()])
    box_lo,box_hi=exp.boxes["DynamicObstacle"]
    all_points=np.vstack([future,traces,box_lo,box_hi]);lo=all_points.min(0)-.06;hi=all_points.max(0)+.06
    for ax in axes:
        for key,(lower,upper) in exp.boxes.items():
            ax.add_patch(Rectangle(lower,*(upper-lower),fc="#bd57ac" if key=="DynamicObstacle" else "#789a77",alpha=.3))
        xx,yy=np.meshgrid(np.linspace(lo[0]-.12,hi[0]+.12,420),np.linspace(lo[1]-.12,hi[1]+.12,420))
        distance=np.sqrt(np.maximum(np.maximum(box_lo[0]-xx,xx-box_hi[0]),0)**2+np.maximum(np.maximum(box_lo[1]-yy,yy-box_hi[1]),0)**2)
        ax.contour(xx,yy,distance,levels=[exp.radius,exp.radius+.02],colors=["#952c83"]*2,linestyles=[":","--"],linewidths=1)
        ax.plot(*exp.boundary[:2],"k*",ms=13,zorder=12,label="B52 fixed")
        ax.set_aspect("equal");ax.grid(alpha=.15);ax.set_xlabel("World X (m)");ax.set_ylabel("World Y (m)")
    for name,r in results.items():
        if r.get("world_poses") and name!="B-LOCAL":
            xy=np.array(r["world_poses"])[:,:2]
            axes[0].plot(*xy.T,"o--",color=colors[name],lw=1.6,ms=3,label=f"{name} future XY")
            axes[0].plot(*xy[2],"s",color=colors[name],ms=6)
        trace=np.array(r["rollout"]["poses"])
        for ax in axes:
            ax.plot(*trace[:,:2].T,color=colors[name],lw=2.7,zorder=6,
                    label=f"{name}: {100*r['rollout']['minimum_clearance_m']:.3f} cm" if ax is axes[1] else None)
        axes[1].plot(*trace[-1,:2],"o",c=colors[name],ms=5,zorder=8)
        axes[1].add_patch(Circle(trace[-1,:2],exp.radius,fill=False,color=colors[name],alpha=.7,lw=1))
    axes[0].plot(*observation[:2],"kx",ms=6,label="FRESH52 observation")
    axes[0].plot(*exp.initial[[0,exp.k],:2].T,":",c="black",lw=1,label=f"Initial F0->F{exp.k} chord")
    axes[0].set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),title="Heading variant: fixed k=2; world XY corrections")
    center=(traces.min(0)+traces.max(0))/2;span=max(float(np.max(traces.max(0)-traces.min(0)))+.23,.28)
    axes[1].set(xlim=(center[0]-span/2,center[0]+span/2),ylim=(center[1]-span/2,center[1]+span/2),title="Original PD, same B52 and 16/72 s")
    axes[0].text(*((box_lo+box_hi)/2),"DynamicObstacle\n0.35 x 0.35 m",ha="center",fontsize=9,color="#713d69")
    axes[0].legend(fontsize=8,loc="lower left");axes[1].legend(fontsize=8,loc="upper left")
    fig.suptitle("Topomap B52: first-chord SE(2) graph variant / one offline solve",fontsize=15)
    fig.text(.5,.04,"Dashed XY: native/corrected futures; squares: index 2. Solid arcs: fixed-command rollouts; circles: final 9 cm footprints.\nB-LOCAL shares RAW future XY. Purple dotted/dashed: contact / 2 cm limits. Only RAW was actually executed.",ha="center",fontsize=8.5)
    fig.tight_layout(rect=(0,.12,1,.94))
    fig.savefig(out/"comparison.png",dpi=180,facecolor="white")
    svg=out/"comparison.svg";fig.savefig(svg,metadata={"Date":None},facecolor="white")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n");plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True);parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();run=args.run.resolve();out=args.out.resolve()
    plan_path=Path(__file__).with_name("topomap_b52_chord_protocol.json")
    base_path=Path(__file__).with_name("minimal_se2_graph_protocol.json")
    base_source=Path(__file__).with_name("minimal_se2_graph.py")
    plan=json.loads(plan_path.read_text());base=json.loads(base_path.read_text())
    assert sha256_file(base_path)==plan["original_protocol_sha256"]
    assert sha256_file(base_source)==plan["original_graph_source_sha256"]
    p={**base,"fresh_id":52,"boundary_tick":1016}
    assert p["horizon_ticks"]==plan["horizon_ticks"]==16
    out.mkdir(parents=True,exist_ok=False);write_json(out/"protocol.json",plan)
    hashes=json.loads((run.parent/"topomap_sudden_01_validation/input_hashes.json").read_text())
    assert all(sha256_file(run/name)==digest for name,digest in hashes.items())
    previous=ROOT/"research/results/isaac6_topomap_b52_graph_20261019"
    preserved={str(path):sha256_file(path) for path in previous.iterdir() if path.is_file()}
    event,boundary,config,local,world=read_before_boundary(run,plan,p)
    old_headings,lengths=derived_headings(world)
    cumulative=np.cumsum(lengths);candidates=np.flatnonzero(cumulative>=p["minimum_heading_segment_m"])
    if len(candidates)==0 or np.any(lengths[1:]<p["minimum_heading_segment_m"]):
        write_json(out/"solver.json",{"calls":0,"status":"INVALID_HEADING_INITIALIZATION"});return
    k=1 if lengths[0]>=p["minimum_heading_segment_m"] else int(candidates[0]+1)
    assert k==plan["frozen_k"]
    try:
        headings,lengths,chord_length=chord_headings(world,k)
    except ValueError as error:
        write_json(out/"solver.json",{"calls":0,"status":"INVALID_HEADING_INITIALIZATION","reason":str(error)});return
    assert chord_length>=p["minimum_heading_segment_m"]
    initial=np.column_stack([world,headings])
    exp=ChordExperiment(initial,boundary,config,p,k)
    algebra=minimal_algebra_checks(initial,boundary)
    original_groups=Experiment.groups(exp,initial)
    variant_groups=exp.groups(initial)
    for name,values in original_groups.items():
        np.testing.assert_array_equal(values[1:] if name=="heading_tangent" else values,
                                      variant_groups[name][1:] if name=="heading_tangent" else variant_groups[name])
    assert variant_groups["heading_tangent"][0]==0
    np.testing.assert_array_equal(variant_groups["minimum_segment"],np.maximum(0,.02-lengths)/p["minimum_segment_sigma_m"])
    raw_command=command_detail(local[2]);np.testing.assert_array_equal(raw_command["command_vw"],[event["v_m_s"],event["w_rad_s"]])
    initial_groups=exp.groups(initial)
    snapshot={"basis_sha":plan["basis_commit"],"execution_sha":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "script_sha256":sha256_file(Path(__file__)),"original_source_sha256":sha256_file(base_source),
        "original_protocol_sha256":sha256_file(base_path),"variant_protocol_sha256":sha256_file(plan_path),
        "fresh_id":52,"sample":0,"boundary":boundary.tolist(),"observation_pose":event["observation_pose"],
        "initial_fresh_poses":initial.tolist(),"local_sample0":local.tolist(),"obstacles":config["obstacles"],"corridor":config["corridor"],
        "heading":{"k":k,"cumulative_distance_m":float(cumulative[k-1]),"direct_chord_m":chord_length,
            "adjacent_lengths_m":lengths.tolist(),"derived_headings_rad":headings.tolist(),"fixed_for_all_iterations":True},
        "pre_solve_validation":{**algebra,"only_first_tangent_residual_changed":"PASS","minimum_adjacent_segment_penalty_unchanged":"PASS"},
        "initial_factor_costs":{key:.5*float(r@r) for key,r in initial_groups.items()},
        "original_solver_settings":p["solver"],"environment":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
        "input_hashes":{name:hashes[name] for name in ("model/derived/0052.npz","events.jsonl","agent_trajectory.csv","scenario.json","dynamic/spawn.json")},
        "no_future_trace_or_fresh53_solver_inputs":True}
    write_json(out/"solve_inputs.json",snapshot)
    print(f"Frozen k={k}; heading variant only; starting the sole solve.",flush=True)
    settings=p["solver"];wall=time.monotonic();cpu=time.process_time()
    try:
        solution=least_squares(exp.residual,np.zeros(24),method=settings["method"],jac=settings["jac"],
            ftol=settings["ftol"],xtol=settings["xtol"],gtol=settings["gtol"],max_nfev=settings["max_nfev"],
            x_scale=np.tile(settings["x_scale_per_pose"],8))
    except Exception as error:
        write_json(out/"solver.json",{"calls":1,"success":False,"status":"SOLVER_EXCEPTION","error":repr(error),
            "wall_s":time.monotonic()-wall,"cpu_process_s":time.process_time()-cpu,"residual_calls":exp.calls})
        raise
    wall=time.monotonic()-wall;cpu=time.process_time()-cpu
    optimized=initial+solution.x.reshape(8,3)
    solved={"calls":1,"success":bool(solution.success),"status":int(solution.status),"message":solution.message,
        "nfev":solution.nfev,"njev":solution.njev,"residual_calls_including_jacobian":exp.calls,"wall_s":wall,"cpu_process_s":cpu,
        "cost":float(solution.cost),"residual_l2":float(np.linalg.norm(solution.fun)),"residual_max_abs":float(np.max(abs(solution.fun))),
        "optimality":float(solution.optimality),"optimized_poses":optimized.tolist(),"residual_vector":solution.fun.tolist()}
    write_json(out/"solver.json",solved)
    print(json.dumps({key:solved[key] for key in ("success","nfev","cost","wall_s")}),flush=True)
    results={name:exp.evaluate(name,poses,local[2]) for name,poses in
             (("RAW",initial),("B-LOCAL",initial),("RIGID",rigid_alignment(initial,boundary)),("GRAPH",optimized))}
    validation=validate_actual_after_solve(run,exp,results["RAW"])
    controls=[]
    with (run/"controller.jsonl").open() as stream:
        for line in stream:
            row=json.loads(line)
            if row["simulation_time_s"]>=1032/72:break
            if row["simulation_time_s"]>=1016/72:
                assert row["waypoint_id"]==52 and row["valid"]
                np.testing.assert_array_equal([row["v_m_s"],row["w_rad_s"]],results["RAW"]["rollout"]["command_vw"])
                controls.append(row["simulation_time_s"])
    assert len(controls)==2
    results["STOP"]={"method":"STOP","world_poses":None,"controller_local_waypoint":None,"selected_world_waypoint":None,
        "controller":{"command_vw":[0.,0.],"unclipped_vw":None,"v_clipped":None,"w_clipped":None},
        "rollout":exp.rollout([0.,0.]),"native_full":None,"native_prefix":None,"note":"Literal stop, no future trajectory or reconciliation"}
    reference=json.loads((previous/"summary.json").read_text())
    for name,prior_name in (("RAW","RAW"),("B-LOCAL","UNCHANGED-B-LOCAL"),("STOP","STOP")):
        r=results[name]["rollout"];old=reference["methods"][prior_name]["rollout"]
        np.testing.assert_array_equal(r["poses"],old["poses"])
        assert r["minimum_clearance_m"]==old["minimum_clearance_m"]
    rows=[]
    for name,r in results.items():
        roll=r["rollout"];cmd=r["controller"];point=r["controller_local_waypoint"]
        rows.append({"method":name,"dx_m":point[0] if point else None,"dy_m":point[1] if point else None,
            "v_m_s":roll["command_vw"][0],"w_rad_s":roll["command_vw"][1],"v_clipped":cmd["v_clipped"],"w_clipped":cmd["w_clipped"],
            "boundary_position_m":r.get("boundary_position_m"),"boundary_tangent_deg":r.get("boundary_tangent_heading_deg"),
            "position_change_rms_m":r.get("position_change_rms_m"),"position_change_max_m":r.get("position_change_max_m"),
            "heading_change_rms_deg":r.get("tangent_heading_change_rms_deg"),"relative_translation_rms_m":r.get("relative_translation_error_rms_m"),
            "relative_heading_rms_deg":r.get("relative_heading_error_rms_deg"),
            "native_full_clearance_m":r["native_full"]["obstacle_clearance_m"] if r["native_full"] else None,
            "native_prefix_clearance_m":r["native_prefix"]["obstacle_clearance_m"] if r["native_prefix"] else None,
            "rollout_clearance_m":roll["minimum_clearance_m"],"margin_met":roll["margin_met"],"overlap":roll["geometric_overlap"],
            "corridor_clearance_m":roll["minimum_corridor_m"],"safe":roll["safe"],"distance_m":roll["distance_m"],
            "end_pose":json.dumps(roll["end_pose"])})
    with (out/"comparison.csv").open("x") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
    for r in results.values():r["rollout"].pop("intervals")
    np.testing.assert_allclose(sum(results["GRAPH"]["factor_costs"].values()),solution.cost,atol=1e-12,rtol=1e-12)
    summary={"variant":plan["variant"],"solver":{k:v for k,v in solved.items() if k not in ("optimized_poses","residual_vector")},
        "heading":snapshot["heading"],"boundary":boundary.tolist(),"boundary_sim_s":1016/72,"horizon_s":16/72,
        "initial_clearances_m":{key:point_clearance(boundary[:2],lo,hi,exp.radius) for key,(lo,hi) in exp.boxes.items()},
        "methods":results,"validation":{**validation,**snapshot["pre_solve_validation"],"actual_controller_ticks":controls,
            "unchanged_raw_blocal_stop_match_previous":"exact","preserved_run_hashes":len(hashes),"preserved_prior_result_files":len(preserved)},
        "limitations":["New first-heading variant; not the unchanged original graph initialization.",
            "Exact scene geometry, one offline solve, no OLD/FRESH correspondence factor or closed-loop test.",
            "Common graph factor cost uses B-local controller semantics; RAW rollout separately retains observation-local input.",
            "Soft 25mm target differs from 20mm pass threshold; fixed B52 initial clearance is below soft target.",
            "Speed/stop effects alone do not establish a unique Graph advantage or reconciliation necessity."]}
    write_json(out/"summary.json",summary)
    plot_comparison(out,exp,np.array(event["observation_pose"]),results)
    assert all(sha256_file(run/name)==digest for name,digest in hashes.items())
    assert all(sha256_file(Path(name))==digest for name,digest in preserved.items())
    assert sha256_file(base_source)==plan["original_graph_source_sha256"] and sha256_file(base_path)==plan["original_protocol_sha256"]
    print(json.dumps({name:{"command":r["rollout"]["command_vw"],"clearance":r["rollout"]["minimum_clearance_m"],
                           "safe":r["rollout"]["safe"],"distance":r["rollout"]["distance_m"]} for name,r in results.items()}),flush=True)


if __name__=="__main__":
    main()
