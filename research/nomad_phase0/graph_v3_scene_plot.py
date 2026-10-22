"""Scene XY views of saved Graph v3 commands. No solver, inference or navigation."""
import argparse
import json
from pathlib import Path

import numpy as np

from nomad_isaac.common import integrate_se2, sha256_file, write_json


METHODS = ["RAW", "RAW+Speed", "RAW+Rate limit", "RIGID", "Graph v2", "Graph v3"]
COLORS = ["#355c86", "#248baf", "#b38318", "#ce6b37", "#8061ac", "#008b78"]
CASES = [
    ("S0_02_F0054", "S0 · 두 번째 정적 장애물 접근 · FRESH 54",
     "S0 selected cases ordered by run/ID: first B with world X in [2.1,2.7]; geometry-only illustration selection"),
    ("S1_P0_F0060", "S1 · 돌발 장애물 장면 · FRESH 60",
     "Previously reported Graph v3 H_chunk 2cm margin failure; deliberately show the retained failure"),
    ("topomap_sudden_01_F0052", "Stress · Topomap sudden · FRESH 52",
     "Previously specified B52 stress case; PD-origin history, PP counterfactual, rejected v3 final iterate"),
]


def replay(record, boundary):
    """Reconstruct the saved 72Hz polyline, without recomputing a controller."""
    points = [np.array(boundary, dtype=float)]
    controls = record["controls"]
    maximum_error = 0.
    for i, control in enumerate(controls):
        assert control["offset_tick"] == len(points)-1
        error = float(np.max(np.abs(points[-1]-control["pose"])))
        maximum_error = max(maximum_error, error)
        np.testing.assert_allclose(points[-1], control["pose"], atol=1e-10, rtol=0)
        stop = controls[i+1]["offset_tick"] if i+1 < len(controls) else record["executed_ticks"]
        for _ in range(stop-control["offset_tick"]):
            points.append(integrate_se2(points[-1], *control["command_vw"], 1/72))
    assert len(points) == record["executed_ticks"]+1
    np.testing.assert_allclose(points[-1], record["end_pose"], atol=1e-10, rtol=0)
    return np.array(points), maximum_error


def draw_geometry(ax, config, overview=False):
    from matplotlib.patches import Rectangle, FancyBboxPatch
    radius_margin = config["agent_radius_m"]+config["required_clearance_m"]
    for box in config["obstacles"]:
        center = np.array(box["center_xy_m"]); size = np.array(box["size_xyz_m"][:2])
        lower = center-size/2
        dynamic = box["id"] == "DynamicObstacle"
        color = "#bf569e" if dynamic else "#80958b"
        if not overview:
            ax.add_patch(FancyBboxPatch(lower-radius_margin, *(size+2*radius_margin),
                boxstyle=f"round,pad=0,rounding_size={radius_margin}", fc="none",
                ec=color, lw=1.1, ls=":", alpha=.85, zorder=0))
        ax.add_patch(Rectangle(lower, *size, fc=color, ec=color, alpha=.32, zorder=0))
    corridor = config["corridor"]
    for y in [-corridor["half_width"], corridor["half_width"]]:
        ax.axhline(y, color="#59616a", lw=2, zorder=1)
    for x in [corridor["xmin"], corridor["xmax"]]:
        ax.axvline(x, color="#59616a", lw=2, zorder=1)


def draw_case(data, output, title):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Rectangle

    case = data["case"]; boundary = np.array(case["boundary"])
    observation = np.array(case["observation_pose"])
    config = case["evaluation_config"]
    paths = {}; errors = []
    for method, info in data["methods"].items():
        paths[method] = {}
        for horizon in ["H_switch", "H_chunk"]:
            path, error = replay(info[horizon], boundary)
            paths[method][horizon] = path
            errors.append(error)
    all_xy = np.vstack([boundary[:2], observation[:2]]+
        [v[h][:, :2] for v in paths.values() for h in v]+
        [np.array(m["world_xy_m"]) for m in data["methods"].values()])
    low = all_xy.min(axis=0)-.13; high = all_xy.max(axis=0)+.13
    # Shared square viewport for all methods, encompassing every saved continuation.
    center = (low+high)/2; span = max(.62, float(max(high-low)))
    limits = [center-span/2, center+span/2]
    fig, axes = plt.subplots(2, 3, figsize=(16, 12))
    fig.subplots_adjust(left=.055, right=.98, top=.795, bottom=.12, wspace=.19, hspace=.34)
    fig.text(.055, .966, title, fontsize=20, weight="bold", color="#1c3345")
    fig.text(.055, .932, "같은 실제 switch B에서 시작한 방법별 PP 궤적", fontsize=14)
    fig.text(.055, .901, "저장된 제어 명령의 오프라인 재구성 · 새 주행/최적화 없음 · 전체 closed-loop 주행이 아님",
             fontsize=10.5, color="#4c5963")
    fig.text(.055, .873, f"B = ({boundary[0]:.3f}, {boundary[1]:.3f}, {boundary[2]:+.3f})   |   "
             f"H_switch = {case['horizon_ticks']/72:.3f}s   |   회색 점선은 충돌 후 수학적 연장",
             fontsize=10.5, color="#4c5963")

    inset = fig.add_axes([.79, .852, .18, .12])
    draw_geometry(inset, config, overview=True)
    inset.set(xlim=(-.3, 4.8), ylim=(-1.65, 1.65))
    inset.set_aspect("equal"); inset.set_xticks([]); inset.set_yticks([])
    inset.scatter(*config["start_pose"][:2], s=15, c="#273846")
    inset.scatter(*config["goal_pose"][:2], s=25, marker="*", c="#273846")
    inset.scatter(*boundary[:2], s=20, marker="D", c="#008b78")
    inset.add_patch(Rectangle(limits[0], span, span, fill=False, ec="#008b78", lw=1.3))
    inset.set_title("전체 장면 / 표시 영역", fontsize=9, pad=3)

    method_metadata = {}
    for ax, method, color in zip(axes.flat, METHODS, COLORS):
        ax.set_aspect("equal")
        ax.set(xlim=(limits[0][0], limits[1][0]), ylim=(limits[0][1], limits[1][1]))
        ax.set_xlabel("World X (m)", fontsize=9); ax.set_ylabel("World Y (m)", fontsize=9)
        ax.grid(alpha=.12); ax.tick_params(labelsize=8)
        draw_geometry(ax, config)
        ax.set_title(method, loc="left", fontsize=14, color=color, weight="bold", pad=10)
        if method not in data["methods"]:
            ax.text(.5, .5, "저장된 Graph v2 결과 없음\n새 solve는 실행하지 않음", transform=ax.transAxes,
                    ha="center", va="center", fontsize=12, color="#666d75")
            method_metadata[method] = {"status": "NOT_AVAILABLE"}
            continue
        info = data["methods"][method]; short = info["H_switch"]; long = info["H_chunk"]
        xy = np.array(info["world_xy_m"]); path = paths[method]["H_chunk"]
        ax.plot(*xy.T, "o--", color=color, lw=1.2, ms=3, alpha=.65, zorder=4)
        collision = long["first_overlap_offset_tick"]
        cutoff = collision if collision is not None else len(path)-1
        if collision is not None:
            ax.plot(*path[collision:, :2].T, color="#a2a6ab", ls=":", lw=1.2, alpha=.75, zorder=2)
        ax.plot(*path[:cutoff+1, :2].T, color=color, lw=2.5, zorder=5)
        ax.plot(*paths[method]["H_switch"][:, :2].T, color="#172c3b", lw=4, zorder=6)
        for fraction in [.33, .72]:
            i = min(max(1, round(cutoff*fraction)), max(1, cutoff-1))
            j = min(cutoff, i+max(2, round(.025*72/.2)))
            if j > i:
                ax.annotate("", path[j, :2], path[i, :2], arrowprops={"arrowstyle":"-|>",
                    "color":color, "lw":1.8, "mutation_scale":13}, zorder=8)
        ax.add_patch(Circle(boundary[:2], config["agent_radius_m"], fc="none", ec="#394956",
                            lw=.8, alpha=.65, zorder=3))
        ax.annotate("", boundary[:2]+.085*np.array([np.cos(boundary[2]), np.sin(boundary[2])]),
                    boundary[:2], arrowprops={"arrowstyle":"->", "color":"#172c3b", "lw":1.4}, zorder=10)
        ax.scatter(*observation[:2], marker="o", fc="white", ec="#545b64", s=25, zorder=9)
        ax.scatter(*boundary[:2], marker="D", c="#172c3b", ec="white", lw=.7, s=36, zorder=10)
        ax.annotate("B", boundary[:2], (5, 6), textcoords="offset points", fontsize=10,
                    weight="bold", color="#172c3b", zorder=12)
        ax.scatter(*path[-1, :2], marker="s", fc="white", ec=color, lw=1.4, s=34, zorder=9)
        if collision is not None:
            ax.scatter(*path[collision, :2], marker="x", c="#c8283b", lw=2.1, s=70, zorder=12)
            ax.add_patch(Circle(path[collision, :2], config["agent_radius_m"], fill=False,
                                ec="#c8283b", lw=1, ls="--", zorder=9))
        converged = info.get("solver", {}).get("success", True)
        status = "충돌 포함" if long["geometric_overlap"] else "2cm 미달" if not long["margin_met"] else "장애물 2cm 충족"
        if long["corridor_intrusion"]: status += " · 복도 침범"
        finish = "chunk 끝 도달" if long["endpoint_reached"] else "60s 평가 제한"
        if not converged: status = "미수렴 최종 iterate · " + status
        ax.text(.025, .975, f"{status}\nH_chunk {long['duration_s']:.2f}s · {finish}", transform=ax.transAxes,
                fontsize=9, color="#a9313a" if not converged or not long["safe"] else "#386b53", va="top",
                bbox={"facecolor":"white", "edgecolor":"none", "alpha":.9, "pad":3}, zorder=15)
        method_metadata[method] = {"horizon_switch_s": short["duration_s"],
            "horizon_chunk_s": long["duration_s"], "chunk_status": long["status"],
            "first_overlap_offset_tick": collision, "minimum_clearance_m": long["minimum_clearance_m"],
            "converged": converged, "native_full_safe": info["native_full"]["safe"],
            "chunk_rollout_safe": long["safe"]}

    handles = [Line2D([], [], c="#172c3b", lw=4, label="H_switch: 다음 실제 switch까지"),
        Line2D([], [], c="#008b78", lw=2.5, label="H_chunk: 같은 경로를 끝까지 추종"),
        Line2D([], [], c="#008b78", ls="--", marker="o", ms=3, label="방법별 8점 경로"),
        Line2D([], [], c="#a2a6ab", ls=":", label="충돌 후 계산된 연장"),
        Line2D([], [], c="#c8283b", marker="x", ls="none", label="첫 geometric overlap")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, .04), ncol=3,
               frameon=False, fontsize=10)
    fig.text(.5, .018, "초록색 박스: 정적 장애물 · 자주색 박스: 동적 장애물 · 박스 바깥 점선: 중심이 지켜야 할 9cm 반경 + 2cm 여유",
             ha="center", fontsize=9.5, color="#4c5963")
    figure = output/f"{case['case_id']}_scene.png"
    fig.savefig(figure, dpi=170, facecolor="white")
    plt.close(fig)
    return {"case_id": case["case_id"], "figure": figure.name, "figure_sha256": sha256_file(figure),
            "viewport": [v.tolist() for v in limits], "maximum_replay_error": max(errors),
            "methods": method_metadata}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font = font_manager.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    plt.rcParams.update({"font.family": font.get_name(), "font.size": 10,
                         "axes.unicode_minus": False, "path.simplify": False})
    files = {case: args.source/"cases"/(case+".json") for case, _, _ in CASES}
    hashes = {str(path): sha256_file(path) for path in files.values()}
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for case, title, reason in CASES:
        result = draw_case(json.loads(files[case].read_text()), args.output, title)
        result["illustration_selection_reason"] = reason
        results.append(result)
    assert all(sha256_file(Path(path)) == digest for path, digest in hashes.items())
    write_json(args.output/"manifest.json", {"scope": "Saved command reconstruction; fixed-B offline counterfactual, not new closed-loop navigation",
        "new_optimization": 0, "new_navigation": 0, "new_inference": 0,
        "input_sha256": hashes, "cases": results,
        "note": "Selected illustrations do not replace aggregate59-case results; post-overlap extensions are grey, not actual collision execution."})
    print(json.dumps({"output": str(args.output), "plots": len(results),
                      "maximum_replay_error": max(r["maximum_replay_error"] for r in results)}))


if __name__ == "__main__":
    main()
