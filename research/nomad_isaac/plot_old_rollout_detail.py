"""Zoom the saved 49--53 predictions and actual execution; no simulator/inference."""
import argparse
import json
from pathlib import Path

import numpy as np

from .clearance import obstacle_bounds, single_obstacle_config
from .common import local_to_world, sha256_file, write_json


def plot(audit, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Rectangle

    report = json.loads((audit/"summary.json").read_text())
    run = Path(report["source_run"])
    hashes = json.loads((audit/"handoff/input_hashes.json").read_text())
    assert all(sha256_file(run/name) == digest for name, digest in hashes.items())
    source_hash = sha256_file(audit/"summary.json")
    config = json.loads((run/"scenario.json").read_text())
    received = {r["id"]: r for r in map(json.loads, (run/"received.jsonl").read_text().splitlines())}
    events = {r["id"]: r for r in map(json.loads, (run/"events.jsonl").read_text().splitlines())}
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True)
    poses = np.column_stack([trace[k] for k in ("x_m", "y_m", "yaw_rad")])
    ids = list(range(49, 54)); hz = config["integration_hz"]
    worlds, markers, segments = {}, [], {}
    for i in ids:
        r = received[i]
        with np.load(run/f"model/derived/{i:04d}.npz", allow_pickle=False) as data:
            worlds[i] = local_to_world(data["metric"][0], r["observation_pose"])
        tick = round(r["observation_sim_s"]*hz)
        np.testing.assert_allclose(r["observation_pose"], poses[tick], atol=1e-12, rtol=0)
        marker = {"id": i, "observation_sim_s": r["observation_sim_s"],
                  "observation_pose": r["observation_pose"], "world_prediction": worlds[i].tolist(),
                  "applied": i in events, "switch_sim_s": None, "switch_pose": None}
        if i in events:
            e = events[i]; start = round(e["application_sim_s"]*hz)
            end = round(events[i+1]["application_sim_s"]*hz) if i+1 in events else len(poses)-1
            np.testing.assert_allclose(e["agent_pose_at_switch"], poses[start], atol=1e-12, rtol=0)
            assert set(trace["incoming_waypoint_id"][start+1:end+1].astype(int)) == {i}
            segments[i] = (start, end)
            marker.update(switch_sim_s=e["application_sim_s"], switch_pose=e["agent_pose_at_switch"],
                          execution_end_sim_s=float(trace["simulation_time_s"][end]),
                          executed_intervals=end-start, command_vw=[e["v_m_s"], e["w_rad_s"]])
        markers.append(marker)
    assert 53 not in events and received[53]["terminal_unapplied"]
    assert report["later_execution"]["collision_command_id"] == 52
    output.mkdir(parents=True, exist_ok=False)
    font = font_manager.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    plt.rcParams.update({"font.family": font.get_name(), "font.size": 10,
                         "svg.fonttype": "path", "svg.hashsalt": "nomad-old-rollout-detail",
                         "path.simplify": False, "axes.unicode_minus": False})
    colors = {49: "#b87906", 50: "#2372bd", 51: "#008b77", 52: "#d13a32", 53: "#8261ae"}
    fig, (pred, actual) = plt.subplots(1, 2, figsize=(15.6, 10.4))
    fig.subplots_adjust(left=.065, right=.97, top=.81, bottom=.30, wspace=.24)
    box = report["placement"]["obstacle"]
    lower, upper = obstacle_bounds(single_obstacle_config(config, box))
    for ax in (pred, actual):
        ax.add_patch(Rectangle(lower, *(upper-lower), fc="#ce82bd", ec="#a14089", alpha=.40, zorder=0))
        ax.plot(*poses[:, :2].T, c="#222b35", lw=3.6, zorder=4)
        ax.add_patch(Circle(poses[-1, :2], config["agent_radius_m"], fill=False,
                            ec="#d13a32", ls=":", lw=1.6, zorder=2))
        ax.scatter(*poses[-1, :2], marker="X", s=95, facecolor="#d13a32", edgecolor="white", lw=1, zorder=12)
        ax.set_aspect("equal"); ax.grid(alpha=.16)
        ax.set_xlabel("World X (m)"); ax.set_ylabel("World Y (m)")
        ax.tick_params(labelsize=9)
    pred.set(xlim=(1.82, 2.62), ylim=(-.43, .27))
    actual.set(xlim=(1.95, 2.34), ylim=(-.17, .22))
    pred.set_title("A  |  예측 49–53과 실제 주행 경로", loc="left", fontsize=13, pad=15)
    actual.set_title("B  |  실제 실행 확대 · 관측 O / 적용 S", loc="left", fontsize=13, pad=15)

    end_labels = {49:(2.38,-.19), 50:(1.83,-.17), 51:(1.83,-.045), 52:(2.07,.235), 53:(2.39,.235)}
    for i in ids:
        w = worlds[i]
        pred.plot(*w.T, "o--", c=colors[i], ms=4, lw=1.8, zorder=5, alpha=.93)
        pred.scatter(*w[2], marker="s", s=65, c=colors[i], edgecolor="white", linewidth=1, zorder=8)
        label = f"{i}" + (" (미적용)" if i == 53 else "")
        pred.annotate(label, w[-1], end_labels[i], color=colors[i], weight="bold", fontsize=12,
                      arrowprops={"arrowstyle":"-", "color":colors[i]}, zorder=9)
    pred.text(2.42,-.31,"동적 장애물\n0.35 × 0.35 m", ha="center", color="#78316a", fontsize=10)
    pred.annotate("실제 중심 경로", poses[round(13.15*hz), :2], (1.83,.20), fontsize=11,
                  arrowprops={"arrowstyle":"->", "color":"#222b35"}, color="#222b35")
    pred.annotate("실제 충돌 시 9 cm footprint", (poses[-1,0], poses[-1,1]-.09), (1.84,-.35),
                  fontsize=10, color="#bb382f", arrowprops={"arrowstyle":"-", "color":"#bb382f"})
    for i, (start,end) in segments.items():
        actual.plot(*poses[start:end+1,:2].T, c=colors[i], lw=5, zorder=5)
        middle = (start+end)//2
        actual.annotate("", poses[middle+2,:2], poses[middle-2,:2], zorder=8,
                        arrowprops={"arrowstyle":"-|>", "color":colors[i], "lw":2.5, "mutation_scale":14})

    obs_targets = {49:(1.958,.17),50:(1.958,.108),51:(1.958,.044),52:(1.958,-.018),53:(1.958,-.102)}
    switch_targets = {49:(2.18,.16),50:(2.18,.085),51:(2.18,.034),52:(2.18,-.026)}
    for m in markers:
        i = m["id"]; c = colors[i]
        actual.scatter(*m["observation_pose"][:2], marker="o", s=60, fc="white", ec=c, lw=1.6, zorder=11)
        text = f"O{i}  {m['observation_sim_s']:.3f}s" + ("\n53은 관측·수신만" if i == 53 else "")
        actual.annotate(text, m["observation_pose"][:2], obs_targets[i], fontsize=9, color=c,
                        arrowprops={"arrowstyle":"-", "color":c, "lw":.8}, zorder=12)
        if m["applied"]:
            actual.scatter(*m["switch_pose"][:2], marker="D", s=60, fc=c, ec="white", lw=.8, zorder=11)
            actual.annotate(f"S{i}  {m['switch_sim_s']:.3f}s", m["switch_pose"][:2], switch_targets[i],
                            fontsize=9, color=c, arrowprops={"arrowstyle":"-", "color":c, "lw":.8}, zorder=12)
    spawn = report["native_audit"]["spawn"]
    actual.scatter(*spawn["pose"][:2], marker="*", s=105, c="#222b35", zorder=11)
    actual.annotate(f"장애물 등장  {spawn['simulation_time_s']:.3f}s", spawn["pose"][:2], (2.11,.198),
                    color="#222b35", fontsize=9, arrowprops={"arrowstyle":"-", "lw":.8}, zorder=12)
    actual.annotate(f"충돌·중단  {trace['simulation_time_s'][-1]:.3f}s\n적용 중인 명령: 52", poses[-1,:2],
                    (2.06,-.15), fontsize=9.5, color="#bc332e",
                    arrowprops={"arrowstyle":"->", "color":"#bc332e", "lw":1}, zorder=12)
    actual.text(2.285,-.105,"동적 장애물\n(일부)", ha="center", fontsize=9, color="#78316a")

    fig.suptitle("장애물 부근 확대: prediction 49 → 50 → 51 → 52 → 53", fontsize=19, weight="bold", y=.97)
    fig.text(.5,.924,"숫자는 prediction ID · 점선은 예측 · 굵은 실선은 실제 주행 · 53은 실제 적용되지 않음",
             ha="center", fontsize=11.5, color="#46525e")
    legend = [Line2D([],[],c="#222b35",lw=3,label="실제 중심 경로"),
              Line2D([],[],c="#6c7480",ls="--",marker="o",label="sample 0 예측 8점"),
              Line2D([],[],c="#6c7480",marker="s",ls="none",label="선택 waypoint index 2"),
              Line2D([],[],c="#6c7480",marker="o",mfc="white",ls="none",label="O: observation pose"),
              Line2D([],[],c="#6c7480",marker="D",ls="none",label="S: 실제 switch pose")]
    fig.legend(handles=legend,loc="lower center",bbox_to_anchor=(.5,.235),ncol=5,frameon=False,fontsize=9)
    table_ax=fig.add_axes([.12,.062,.76,.147]);table_ax.axis("off")
    segment_reports={r["id"]:r for r in report["later_execution"]["applied_segments"]}
    cells=[]
    for m in markers:
        i=m["id"]
        cells.append([str(i),f"{m['observation_sim_s']:.3f}",
                      f"{m['switch_sim_s']:.3f}" if m['applied'] else "미적용",
                      f"({m['command_vw'][0]:.2f}, {m['command_vw'][1]:+.3f})" if m['applied'] else "없음",
                      f"{segment_reports[i]['executed_dynamic_clearance_lower_m']*100:+.3f} cm" if m['applied'] else "실행 구간 없음"])
    table=table_ax.table(cellText=cells,colLabels=["ID","관측 시각 (sim s)","적용 시각 (sim s)","원본 PD (v m/s, w rad/s)","실제 구간 최소 clearance"],
                        colWidths=[.07,.20,.20,.27,.26],cellLoc="center",bbox=[0,0,1,1])
    table.auto_set_font_size(False);table.set_fontsize(9)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor("#e0e5eb");cell.set_linewidth(.6)
        if row==0:cell.set_facecolor("#eef2f6");cell.set_text_props(weight="bold")
        elif col==0:cell.set_text_props(color=colors[ids[row-1]],weight="bold")
    fig.text(.5,.025,"예측은 각 observation pose 기준, 실제 경로는 저장된 72 Hz pose 그대로 사용. Clearance는 49만 등장 이후, 50–52는 각 적용 구간 기준.",
             ha="center",fontsize=9,color="#46525e")
    fig.savefig(output/"old_rollout_detail.png",dpi=180,facecolor="white")
    svg=output/"old_rollout_detail.svg";fig.savefig(svg,metadata={"Date":None},facecolor="white")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n");plt.close(fig)
    assert all(sha256_file(run/name)==digest for name,digest in hashes.items())
    assert sha256_file(audit/"summary.json")==source_hash
    write_json(output/"manifest.json",{"source_run":str(run),"source_audit":str(audit),
        "source_audit_sha256":source_hash,"preserved_run_inputs":len(hashes),"input_hash_manifest":str(audit/"handoff/input_hashes.json"),
        "ids":ids,"markers":markers,"segments_match_actual_incoming_ids":True,
        "observation_and_switch_poses_match_72hz_trace":True,"applied_ids":[49,50,51,52],"terminal_unapplied_ids":[53],
        "new_navigation_count":0,"new_inference_count":0,"prediction_anchor":"observation_pose",
        "collision_pose":poses[-1].tolist(),"collision_sim_s":float(trace['simulation_time_s'][-1]),
        "figure_sha256":{p.name:sha256_file(p) for p in [output/"old_rollout_detail.png",svg]}})


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();plot(args.audit.resolve(),args.output.resolve())
