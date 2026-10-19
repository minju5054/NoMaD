"""Prepare the declared 2s map using byte-identical saved reference images."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from .common import ROOT, sha256_file, write_json
from .topomap import reference_rows
from .topomap_report import validate_map

PROTOCOL = Path(__file__).with_name("topomap_spacing_protocol.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    parent_path = args.parent.resolve()
    parent, _ = validate_map(parent_path)
    protocol = json.loads(PROTOCOL.read_text())
    expected = reference_rows(Path(parent["source_run"]), parent["scenario"], protocol["reference_spacing_sim_s"])
    selected = [node for node in parent["nodes"] if node["reference_pose_row"] in {i for i, _ in expected}]
    assert [node["node_id"] for node in selected] == protocol["parent_node_ids"]
    assert len(selected) == protocol["node_count"] == len(expected)
    parent_hash = sha256_file(parent_path)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/"rgb").mkdir()
    nodes = []
    for index, original in enumerate(selected):
        filename = f"rgb/{index:04d}.png"
        shutil.copyfile(parent_path.parent/original["rgb_file"], args.out/filename)
        assert sha256_file(args.out/filename) == original["png_sha256"]
        nodes.append({**original, "node_id": index, "parent_node_id": original["node_id"], "rgb_file": filename})
    manifest = {**parent, "nodes": nodes, "node_count": len(nodes),
                "spacing_sim_s": protocol["reference_spacing_sim_s"],
                "parent_manifest": str(parent_path), "parent_manifest_sha256": parent_hash,
                "parent_protocol_sha256": parent["protocol_sha256"], "protocol_sha256": sha256_file(PROTOCOL),
                "subset_git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "new_render_count": 0,
                "note": "2s subset plus original final goal-entry frame. Node IDs reindexed; original render SHA and RGB bytes preserved."}
    write_json(args.out/"manifest.json", manifest)
    _, checks = validate_map(args.out/"manifest.json")
    assert sha256_file(parent_path) == parent_hash
    print(json.dumps({"manifest": str(args.out/"manifest.json"), "checks": checks,
                      "original_node_ids": protocol["parent_node_ids"]}))


if __name__ == "__main__":
    main()
