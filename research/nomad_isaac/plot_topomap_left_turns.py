"""Show saved Topomap FRESH 50--53 commands, native paths, and execution."""
import argparse
import json
from pathlib import Path

import numpy as np

from .clearance import obstacle_bounds, single_obstacle_config
from .common import local_to_world, original_controller, sha256_file, write_json


def plot(audit, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Rectangle

    report = json.loads((audit / "summary.json").read_text())
    run = Path(report["run"])
    hashes = json.loads((audit / "input_hashes.json").read_text())
    assert all(sha256_file(run / p) == h for p, h in hashes.items())
    source_hash = sha256_file(audit / "summary.json")
    raw = json.loads((run / "summary.json").read_text())
    config = raw["scenario"]
    events = {e["id"]: e for e in map(json.loads, (run / "events.jsonl").read_text().splitlines())}
    controls = list(map(json.loads, (run / "controller.jsonl").read_text().splitlines()))
    trace = np.genfromtxt(run / "agent_trajectory.csv", delimiter=",", names=True)
    pose = np.column_stack([trace[k] for k in ("x_m", "y_m", "yaw_rad")])
    time = trace["simulation_time_s"]
    ids = [50, 51, 52, 53]
    controller = original_controller()
    segments, worlds, records = {}, {}, []
    for i in ids:
        e = events[i]
        start = round(e["application_sim_s"] * config["integration_hz"])
        end = round(events[i+1]["application_sim_s"] * config["integration_hz"]) if i+1 in events else len(pose)-1
        obs_tick = round(e["observation_sim_s"] * config["integration_hz"])
        np.testing.assert_allclose(pose[start], e["agent_pose_at_switch"], atol=1e-12, rtol=0)
        np.testing.assert_allclose(pose[obs_tick], e["observation_pose"], atol=1e-12, rtol=0)
        assert np.all(trace["incoming_waypoint_id"][start+1:end+1] == i)
        with np.load(run / f"model/derived/{i:04d}.npz", allow_pickle=False) as z:
            local = z["metric"][0]
        np.testing.assert_array_equal(local[2], e["selected_waypoint_m"])
        vw = controller(local[2].tolist())
        np.testing.assert_array_equal(vw, [e["v_m_s"], e["w_rad_s"]])
        ct = [c for c in controls if c["waypoint_id"] == i]
        assert ct and all(c["valid"] and (c["v_m_s"], c["w_rad_s"]) == tuple(vw) for c in ct)
        np.testing.assert_allclose(np.diff(pose[start:end+1, 2]),
                                   vw[1] * np.diff(time[start:end+1]), atol=1e-12, rtol=0)
        assert vw[1] > 0
        worlds[i] = local_to_world(local, e["observation_pose"])
        segments[i] = (start, end)
        records.append({"id": i, "switch_sim_s": float(time[start]), "end_sim_s": float(time[end]),
                        "v_m_s": vw[0], "w_rad_s": vw[1], "subgoal": e["topomap"]["selected_subgoal_id"],
                        "start_yaw_deg": float(np.degrees(pose[start, 2])),
                        "end_yaw_deg": float(np.degrees(pose[end, 2])),
                        "controller_ticks": len(ct), "native_world_xy": worlds[i].tolist()})
    assert raw["termination_reason"] == "geometric_collision"
    assert report["later_execution"]["collision_command_id"] == 53
    output.mkdir(parents=True, exist_ok=False)
    font = font_manager.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    plt.rcParams.update({"font.family": font.get_name(), "font.size": 10, "axes.unicode_minus": False,
                         "svg.fonttype": "path", "svg.hashsalt": "nomad-topomap-left-turns", "path.simplify": False})
    colors = {50: "#2372bd", 51: "#008572", 52: "#d48513", 53: "#8852aa"}
    fig = plt.figure(figsize=(15, 8.5))
    gs = fig.add_gridspec(2, 2, left=.065, right=.965, bottom=.22, top=.81,
                          width_ratios=[1.05, 1], wspace=.30, hspace=.34)
    xy = fig.add_subplot(gs[:, 0]); angular = fig.add_subplot(gs[0, 1]); yaw = fig.add_subplot(gs[1, 1], sharex=angular)
    box = report["placement"]["obstacle"]
    lo, hi = obstacle_bounds(single_obstacle_config(config, box))
    xy.add_patch(Rectangle(lo, *(hi-lo), fc="#ce82bd", ec="#a14089", alpha=.35))
    xy.text(2.38, .257, "동적 장애물 (상단 일부)", ha="center", color="#78316a", fontsize=10)
    margin_y = hi[1] + config["agent_radius_m"] + config["required_clearance_m"]
    xy.plot([lo[0], hi[0]], [margin_y, margin_y], color="#87919b", ls=":", lw=1.3)
    xy.text(2.48, margin_y+.006, "2 cm 여유의\n중심 경계", color="#67717b", fontsize=8.5, ha="center")
    before = segments[50][0]
    xy.plot(*pose[970:before+1, :2].T, color="#a7afb7", lw=3)
    switch_labels = {50:(2.156,.472), 51:(2.156,.438), 52:(2.156,.402), 53:(2.156,.361)}
    tail_labels = {50:(2.253,.342), 51:(2.31,.555), 52:(2.315,.622), 53:(2.445,.633)}
    for r in records:
        i = r["id"]; c = colors[i]; start, end = segments[i]; w = worlds[i]
        xy.plot(*w.T, "o--", c=c, ms=3.6, lw=1.5, alpha=.85, zorder=4)
        xy.scatter(*w[2], marker="s", c=c, s=55, ec="white", lw=.7, zorder=6)
        xy.annotate(f"예측 {i}", w[-1], tail_labels[i], color=c, fontsize=10,
                    arrowprops={"arrowstyle":"-", "color":c, "lw":.8})
        xy.plot(*pose[start:end+1,:2].T, c=c, lw=4.5, zorder=7)
        xy.scatter(*pose[start,:2], marker="D", s=48, c=c, ec="white", lw=.6, zorder=8)
        xy.annotate(f"B{i}", pose[start,:2], switch_labels[i], color=c, fontsize=10, weight="bold",
                    arrowprops={"arrowstyle":"-", "color":c, "lw":.8}, zorder=10)
        middle = (start+end)//2
        if end-start >= 4:
            xy.annotate("", pose[middle+2,:2], pose[middle-2,:2], zorder=9,
                        arrowprops={"arrowstyle":"-|>", "color":c, "lw":2, "mutation_scale":13})
        a, b = time[start], time[end]
        angular.axvspan(a, b, color=c, alpha=.06)
        angular.plot([a,b], [r["w_rad_s"]]*2, c=c, lw=4, solid_capstyle="butt")
        ticks = [x for x in controls if x["waypoint_id"] == i]
        angular.scatter([x["simulation_time_s"] for x in ticks], [x["w_rad_s"] for x in ticks],
                        c=c, s=28, ec="white", lw=.6, zorder=6)
        angular.text((a+b)/2, .485, str(i), color=c, ha="center", weight="bold", fontsize=12)
        angular.text((a+b)/2, .435, f"SG {r['subgoal']}", color=c, ha="center", fontsize=8)
        yaw.plot(time[start:end+1], np.degrees(pose[start:end+1,2]), c=c, lw=3)
        yaw.scatter(a, r["start_yaw_deg"], c=c, s=30, zorder=4)
    xy.add_patch(Circle(pose[-1,:2], config["agent_radius_m"], fill=False, ec="#c7373b", lw=1.5, ls=":"))
    xy.scatter(*pose[-1,:2], marker="X", s=85, c="#c7373b", ec="white", lw=.8, zorder=12)
    xy.annotate("충돌·중단 14.375 s\n53 적용 중 / 9 cm footprint", pose[-1,:2], (2.374,.318),
                fontsize=9, color="#bd3037", arrowprops={"arrowstyle":"->", "color":"#bd3037", "lw":.8})
    xy.set(xlim=(2.14,2.55), ylim=(.235,.655), xlabel="World X (m)", ylabel="World Y (m)")
    xy.set_aspect("equal"); xy.grid(alpha=.16)
    xy.set_title("A  |  native 예측과 실제 실행 경로", loc="left", fontsize=12, pad=14)
    angular.set_title("B  |  실제 적용 각속도: 모두 w > 0", loc="left", fontsize=12, pad=14)
    angular.axhline(0, c="#6e7780", lw=1)
    angular.axhline(.4, c="#b2bac2", ls=":", lw=.8, zorder=0)
    angular.text(13.68,.27,"50: +0.3401     51·52·53: +0.4000 rad/s", fontsize=10)
    angular.text(13.68,.07,"양수 = 로봇 기준 왼쪽 회전 (반시계)", fontsize=10, color="#46525e")
    angular.set(ylim=(-.055,.54), ylabel="각속도 w (rad/s)")
    angular.tick_params(labelbottom=False); angular.grid(axis="x", alpha=.15)
    yaw.set_title("C  |  저장된 실제 yaw: 계속 증가", loc="left", fontsize=12, pad=10)
    yaw.set(xlim=(13.64,14.42), ylim=(-48,-27), xlabel="Simulation time (s)", ylabel="World yaw (°)")
    yaw.set_xticks([13.666666667,13.888888889,14.111111111,14.333333333],
                  ["13.667\nB50","13.889\nB51","14.111\nB52","14.333\nB53"])
    yaw.grid(alpha=.18)
    yaw.annotate(f"{np.degrees(pose[-1,2]):.2f}° · 충돌", (time[-1],np.degrees(pose[-1,2])),
                 (13.96,-28.4), fontsize=9, color="#bd3037", arrowprops={"arrowstyle":"-", "color":"#bd3037"})
    fig.suptitle("FRESH 50 → 51 → 52 → 53: 왼쪽 회전 명령 유지", fontsize=20, weight="bold", y=.965)
    fig.text(.5,.911,"2초 Topomap sudden-obstacle 저장 기록  |  네 prediction 모두 실제 적용  |  회전 부호 반전 없음",
             ha="center", fontsize=11, color="#46525e")
    handles = [Line2D([],[],c="#56616c",lw=4,label="굵은 실선: 실제 72 Hz 중심 경로"),
               Line2D([],[],c="#56616c",ls="--",marker="o",label="점선: sample 0 native 8점"),
               Line2D([],[],c="#56616c",ls="none",marker="s",label="선택 waypoint index 2"),
               Line2D([],[],c="#56616c",ls="none",marker="D",label="B: 실제 switch pose")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5,.115), ncol=2, frameon=False, fontsize=10)
    fig.text(.5,.070,"왼쪽 회전은 yaw 증가를 뜻합니다. 이 구간은 yaw < 0이므로 world Y가 감소하면서도 왼쪽으로 회전합니다.",
             ha="center", fontsize=10, color="#36424f")
    fig.text(.5,.035,"예측은 각 observation pose 기준이며 실제 PD arc와 다릅니다. 양의 회전 명령 자체가 장애물 회피 성공을 뜻하지 않습니다.",
             ha="center", fontsize=9.5, color="#596570")
    fig.savefig(output / "fresh_50_53_left_turns.png", dpi=180, facecolor="white")
    svg = output / "fresh_50_53_left_turns.svg"
    fig.savefig(svg, metadata={"Date":None}, facecolor="white")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)
    assert all(sha256_file(run / p) == h for p, h in hashes.items())
    assert sha256_file(audit / "summary.json") == source_hash
    write_json(output / "manifest.json", {"source_run":str(run), "source_audit":str(audit),
        "source_audit_sha256":source_hash, "preserved_run_hashes":len(hashes), "ids":ids,
        "records":records, "original_pd_and_controller_ticks_match":True,
        "switch_observation_poses_and_execution_ids_match":True, "yaw_increment_matches_w_dt":True,
        "prediction_anchor":"observation_pose", "new_navigation":0, "new_inference":0,
        "figure_sha256":{p.name:sha256_file(p) for p in [output/"fresh_50_53_left_turns.png",svg]}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.audit.resolve(), args.output.resolve())
