"""One post-hoc recheck: saved-depth accuracy, map replay, then unchanged R3 gate."""
import argparse,ast,inspect,json,types,subprocess,multiprocessing as mp
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean,dump,csv_write
from nomad_phase20c import offline as old
from .detour_known import radial_reference
from .shadow import shadow_kernel
from .map_replay import accuracy,rebuild_events
from .pool import initialize,ping
from .recheck_pool import solve_event

HERE=ROOT/'research/nomad_phase20c';OUT=ROOT/'research/results/phase20c_shadow_recheck'
REPLAY=ROOT.parent/'artifacts/isaac6/phase20c_shadow_replay_01'


def inventory(inputs):
    # The authorized reference no longer requires a NoMaD packet. Preserve the
    # original inventory logic, permitting None only in packet provenance.
    tree=ast.parse(inspect.getsource(old.inventory));changes=[]
    class OptionalPacket(ast.NodeTransformer):
        def visit_Assert(self,node):
            if ast.unparse(node.test)=='packet is not None':changes.append('assert');return ast.Pass()
            return self.generic_visit(node)
        def visit_If(self,node):
            node=self.generic_visit(node)
            if ast.unparse(node.test)=="packet['id'] not in validated":
                node.test=ast.BoolOp(op=ast.And(),values=[ast.parse('packet is not None',mode='eval').body,node.test]);changes.append('validation')
            return node
        def visit_keyword(self,node):
            if node.arg in ('packet_id','observation_pose','sample_observation_age_s'):
                node.value=ast.IfExp(test=ast.parse('packet is not None',mode='eval').body,body=node.value,orelse=ast.Constant(None));changes.append(node.arg)
            return node
    tree=OptionalPacket().visit(tree);assert len(changes)==5,changes
    ns={**old.__dict__,'reference_direction':radial_reference}
    exec(compile(ast.fix_missing_locations(tree),old.__file__,'exec'),ns)
    return ns['inventory'](inputs)


def run():
    assert not OUT.exists() and not REPLAY.exists(),'No overwrite or automatic retry'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Freeze changes before evaluation'
    protocol=json.loads((HERE/'shadow_protocol.json').read_text());inputs=old.Inputs()
    for file,h in protocol['protected_sha256'].items():assert sha256_file(ROOT/file)==h;inputs.track(ROOT/file)
    for file in HERE.glob('*'):
        if file.is_file():inputs.track(file)
    events,excluded,checks=inventory(inputs);assert events
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();OUT.mkdir(parents=True)
    dump(OUT/'protocol.json',protocol);dump(OUT/'events_before_map_replay.json',events);dump(OUT/'excluded_runs.json',excluded)
    dump(OUT/'trigger_checks.json',checks);dump(OUT/'example_ids.json',[e['event_id'] for e in events[:4]])
    print(f'[inventory] {len(events)} events; negative-X references={sum(e["u_ref"][0]<0 for e in events)}',flush=True)
    shadow_kernel()
    comparison=accuracy(OUT,inputs)
    rebuild_events(events,REPLAY,inputs,OUT)
    dump(OUT/'events_before_solve.json',events);dump(OUT/'input_manifest.json',dict(git_sha=sha,sha256=inputs.hashes))
    context=mp.get_context('spawn');ready=context.Queue();solutions=[];examples={}
    with ProcessPoolExecutor(max_workers=4,mp_context=context,initializer=initialize,initargs=(ready,)) as pool,(OUT/'solutions.jsonl').open('x') as log:
        futures=[pool.submit(ping) for _ in range(4)];pids=[ready.get(timeout=90) for _ in range(4)];assert len(set(pids))==4
        for f in futures:f.result()
        for e in events:
            result=solve_event(pool,{k:e[k] for k in ('B','u_ref','snapshot_file')})
            e.update(seven_wall_s=result['seven_wall_s'],selected_initialization=result['selected'],accepted=result['selected'] is not None)
            for r in result['results']:
                r.update(event_id=e['event_id'],run=e['run'],scene=e['scene'],oracle_clearance_m=old.oracle_path(r['path'],e['oracle_config']) if r['path'] is not None else None)
                log.write(json.dumps(clean(r),allow_nan=False)+'\n');log.flush();solutions.append({k:v for k,v in r.items() if k not in ('path','initial_path')})
            roll=None
            if e['accepted']:
                r=result['results'][result['selected']];roll=old.rollout(e['B'],r['path'],e['previous_v'],e['oracle_config'])
                e.update(selected_oracle_clearance_m=r['oracle_clearance_m'],selected_progress_m=r['progress_m'],selected_unknown_fraction=r['unknown_fraction'],
                    selected_near_unknown_fraction=r['near_unknown_fraction'],selected_far_unknown_fraction=r['far_unknown_fraction'],
                    rollout_overlap=roll['overlap'],rollout_minimum_clearance_m=roll['minimum_clearance_m'],rollout_distance_m=roll['distance_m'],
                    rollout_alignment=roll['trigger_S'],rollout_rotation_s=roll['rotation_time_s'],**old.gap_direction(r['path'],e))
            if e['event_id']<4:examples[str(e['event_id'])]=dict(event=e,result=result,rollout=roll)
            if (e['event_id']+1)%10==0:print(f'[R3 recheck] {e["event_id"]+1}/{len(events)}',flush=True)
    verdict=old.decision(events,solutions);selected=[e for e in events if e['accepted']]
    verdict.update(assessment_label='사후 수정 후 재점검',negative_world_x_references=sum(e['u_ref'][0]<0 for e in events),
        accepted_unknown_median=float(np.median([e['selected_unknown_fraction'] for e in selected])) if selected else None,
        accepted_unknown_max=max((e['selected_unknown_fraction'] for e in selected),default=None),
        accepted_far_unknown_max=max((e['selected_far_unknown_fraction'] for e in selected),default=None),
        accepted_paths_with_unknown=sum(e['selected_unknown_fraction']>0 for e in selected))
    csv_write(OUT/'events.csv',[{k:v for k,v in e.items() if k!='oracle_config'} for e in events]);csv_write(OUT/'initializations.csv',solutions)
    dump(OUT/'decision.json',verdict);dump(OUT/'examples.json',examples)
    from .recheck_report import render
    render(OUT,events,solutions,verdict,examples,comparison,excluded,sha,protocol)
    for file,h in inputs.hashes.items():assert sha256_file(file)==h,file
    for e in events:assert sha256_file(e['snapshot_file'])==e['rebuilt_snapshot_sha256']
    dump(OUT/'complete.json',dict(git_sha=sha,events=len(events),initializations=len(solutions),label=verdict['label'],
        map_accuracy_runs=24,map_accuracy_conditions=2,new_render=0,new_navigation=0,new_NoMaD_inference=0,input_hashes_unchanged=True))
    print(json.dumps(clean(verdict)),flush=True)


def publish():
    assert (OUT/'complete.json').exists()
    ignore=OUT/'.gitignore'
    if not ignore.exists():ignore.write_text('/solutions.jsonl\n/map_samples.csv\n/map_updates.csv\n/event_map_updates.csv\n')
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    paths=['research/nomad_phase20c',str(OUT.relative_to(ROOT)),'docs/PHASE20C_SHADOW_RECHECK.md']
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in OUT.glob('*.png')]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Record Phase20C occlusion and start-direction posthoc recheck'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    if OUT.exists():assert (OUT/'complete.json').exists(),'Partial evaluation retained; no automatic repeat'
    else:run()
    if a.publish:publish()

if __name__=='__main__':main()
