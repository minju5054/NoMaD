"""Minimal regression for the exact upstream NoMaD window/selection rules."""
import ast
from types import SimpleNamespace

import numpy as np

from nomad_isaac.common import ROOT
from nomad_isaac.topomap import candidate_range, select_subgoal


def official_assignments():
    tree = ast.parse((ROOT / "deployment/src/navigate.py").read_text())
    assignments = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Assign)), key=lambda n: n.lineno)
    result = []
    for name in ("start", "end", "min_idx", "closest_node", "sg_idx"):
        candidates = [n for n in assignments if isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if name == "closest_node":
            candidates = [n for n in candidates if isinstance(n.value, ast.BinOp) and
                          isinstance(n.value.left, ast.Name) and n.value.left.id == "min_idx"]
        result.append(candidates[0])
    return compile(ast.Module(body=result, type_ignores=[]), "upstream_navigate_selection", "exec")


def test_official_windows_and_threshold_ties():
    official = official_assignments()
    for closest in (0, 4, 10, 25):
        start, end = candidate_range(closest, 25)
        for minimum in (2.999, 3., 3.001):
            distances = np.full(end-start+1, 9.)
            index = min(2, len(distances)-1)
            distances[index] = minimum
            namespace = {"np": np, "args": SimpleNamespace(radius=4, close_threshold=3),
                         "closest_node": closest, "goal_node": 25, "dists": distances,
                         "obsgoal_cond": np.zeros((len(distances), 2))}
            exec(official, namespace)
            actual_closest, selected, relative = select_subgoal(distances, start)
            assert (start, end) == (namespace["start"], namespace["end"])
            assert (actual_closest, relative) == (namespace["closest_node"], namespace["sg_idx"])
            assert selected == start+relative
    assert candidate_range(10, 25) == (6, 15)  # 10 candidates, intentionally asymmetric.
    assert select_subgoal([1., 1., 2.], 4) == (4, 5, 1)  # NumPy argmin first tie.
    assert select_subgoal([9., 1.], 24) == (25, 25, 1)  # Final node clamp.
    assert select_subgoal([1., 9., 9.], 6)[0] < 10  # Backwards localization allowed.
