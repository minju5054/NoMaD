"""Deterministic saved-input selection, before any method results are computed."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,local_to_world,sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase20.metrics import rows
from nomad_phase20c.detour_known import radial_reference

OUT=ROOT/'research/results/phase23o'
def evenly(events,n):
    if not events:return []
    times=np.array([e['application_sim_s'] for e in events]);targets=np.linspace(times[0],times[-1],n)
    return sorted(set(int(np.argmin(np.abs(times-t))) for t in targets))

class Builder:
    def __init__(self):self.hashes={};self.excluded=[];self.cached=None
    def track(self,p):
        p=Path(p).resolve();self.hashes.setdefault(str(p),sha256_file(p));return p
    def load(self,run):
        run=Path(run)
        if self.cached and self.cached['run']==run:return self.cached
        config=json.loads(self.track(run/'scenario.json').read_text());events=rows(self.track(run/'events.jsonl'));rr,poses=trace(run);self.track(run/'agent_trajectory.csv')
        apps=rows(self.track(run/'phase16_applications.jsonl')) if (run/'phase16_applications.jsonl').exists() else rows(self.track(run/'repair.jsonl'))
        updates=rows(self.track(run/'depth/updates.jsonl'));spawn=json.loads(self.track(run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
        manifest=json.loads(self.track(config['topomap_manifest']).read_text())
        self.cached=dict(run=run,config=config,events=events,trace=rr,poses=poses,apps=apps,updates=updates,spawn=spawn,map=manifest);return self.cached
    def case(self,d,e,split,group,scene,index,method,identity,override=None):
        override=override or {};tick=int(override.get('tick',round(e['application_sim_s']*72)));B=d['poses'][tick].tolist()
        if 'B' in override:np.testing.assert_allclose(B,override['B'],atol=1e-12,rtol=0)
        meta=e.get('depth_snapshot') or e.get('phase16',{}).get('selection',{}).get('snapshot')
        file=override.get('snapshot_file',meta['file'] if meta else None)
        if file is None:raise ValueError('Missing available depth snapshot')
        self.track(file);native=np.array([local_to_world(np.array(x),e['observation_pose']) for x in e['overnight_metric_samples']]);assert native.shape==(8,8,2)
        apps=[r for r in d['apps'] if round(r.get('simulation_time_s',r.get('tick',0)/72)*72)<tick and (r.get('world_xy') or r.get('path_world'))]
        old=apps[-1].get('world_xy',apps[-1].get('path_world')) if apps else None
        previous=[float(d['trace'][tick][k]) for k in ('v_m_s','w_rad_s')]
        u,source=radial_reference(d['poses'],tick);oracle=dict(d['config']);oracle['obstacles']=list(oracle.get('obstacles',[]))
        if d['spawn'] and d['spawn']['tick']<=tick:oracle['obstacles'].append(d['spawn']['obstacle'])
        closest=int(e['topomap']['closest_node']);node=d['map']['nodes'][min(closest+1,len(d['map']['nodes'])-1)];direction=np.asarray(node['world_pose'])[:2]-np.asarray(B)[:2];norm=np.linalg.norm(direction)
        direction=direction/norm if norm>1e-12 else np.array([np.cos(B[2]),np.sin(B[2])])
        return dict(case_id=identity,split=split,group=group,scene=scene,index=index,source_method=method,run=str(d['run']),fresh_id=e['id'],tick=tick,B=B,previous_vw=previous,
            samples_world=native.tolist(),old_path=old,old_source=apps[-1].get('kind') if apps else None,snapshot_file=str(file),snapshot_sha256=self.hashes[str(Path(file).resolve())],
            trigger=override.get('trigger'),baseline_u_ref=override.get('u_ref',u.tolist()),baseline_u_source=source,evaluation_direction=direction.tolist(),oracle_config=oracle,spawn=d['spawn'],
            topomap_closest=closest,topomap_next_node=min(closest+1,len(d['map']['nodes'])-1))
    def build(self):
        train=[];evaluation=[];records=json.loads(self.track(ROOT/'research/results/phase18/runs.json').read_text())
        for r in sorted(records,key=lambda r:(r['index'],r['scene'],r['method'])):
            if r['index'] not in range(66,74):continue
            if r['technical_validation']!='PASS':self.excluded.append(dict(run=r['output'],reason='TECHNICAL_FAILURE'));continue
            d=self.load(r['output']);events=[e for e in d['events'] if 'application_sim_s' in e and 'overnight_metric_samples' in e and 'topomap' in e]
            split='training' if r['index']<70 else 'evaluation';n=3 if split=='training' else 10;chosen=evenly(events,n);failure_ids=[]
            if split=='evaluation' and not r['success']:
                tail=[(i,e) for i,e in enumerate(events) if e['application_sim_s']>=r['duration_s']-10]
                failure_ids=[tail[i][0] for i in evenly([e for _,e in tail],5)];chosen=sorted(set(chosen+failure_ids))
            target=train if split=='training' else evaluation
            for i in chosen:
                c=self.case(d,events[i],split,'static',r['scene'],r['index'],r['method'],f'{split[0].upper()}S{len(target):04d}')
                c['failure_window_added']=i in failure_ids;target.append(c)
        previous=json.loads(self.track(ROOT/'research/results/phase22o/manifest.json').read_text())
        for split,collection in [('training',train),('evaluation',evaluation)]:
            for old in previous[split]:
                d=self.load(old['run']);eligible=[e for e in d['events'] if e.get('application_sim_s',1e9)<=old['time_s']+1e-12 and 'overnight_metric_samples' in e]
                if not eligible:raise ValueError('No FRESH available at saved trigger: '+old['case_id'])
                c=self.case(d,eligible[-1],split,'sudden',old['scene'],old['index'],old['method'],f'{split[0].upper()}D{len(collection):04d}',dict(tick=old['tick'],B=old['B'],snapshot_file=old['snapshot_file'],trigger=old['trigger'],u_ref=old['u_ref']))
                c['phase22o_case_id']=old['case_id'];collection.append(c)
        root=ROOT.parent/'artifacts/isaac6/phase22_l2b_rerun_01'
        for file in sorted((root/'metrics').glob('L2B_*.json')):
            r=json.loads(self.track(file).read_text())
            if r['technical_validation']!='PASS':continue
            d=self.load(r['output']);jobs=[]
            for e in rows(self.track(d['run']/'repair.jsonl')):
                if e['event']=='SUBMIT':jobs.append(dict(e,trigger='A'))
            for e in rows(self.track(d['run']/'detour.jsonl')):
                if e['event']=='TRIGGER' and e['trigger']=='B':jobs.append(e)
            for j in sorted(jobs,key=lambda j:j['simulation_time_s']):
                tick=round(j['simulation_time_s']*72);available=[e for e in d['events'] if e['application_sim_s']<=j['simulation_time_s']+1e-12]
                c=self.case(d,available[-1],'evaluation','sudden','L2B',r['index'],r['method'],f'ED{len(evaluation):04d}',dict(tick=tick,B=j['B'],snapshot_file=j['depth_snapshot']['file'],trigger=j['trigger'],u_ref=j.get('u_ref',radial_reference(d['poses'],tick)[0].tolist())))
                evaluation.append(c)
        key=lambda c:(c['run'],c['tick']);assert not ({key(c) for c in train}&{key(c) for c in evaluation})
        assert not ({c['run'] for c in train}&{c['run'] for c in evaluation})
        failed=next(c for c in evaluation if c['scene']=='SLW' and c.get('failure_window_added'))
        examples=[max((c for c in evaluation if c['run']==failed['run']),key=lambda c:c['tick'])['case_id'],
            next(c['case_id'] for c in evaluation if c['scene']=='L2A' and c['index']==111 and c['source_method']=='M3_GRAPH'),
            min((c for c in evaluation if c['scene']=='LC'),key=lambda c:np.linalg.norm(np.array(c['B'][:2])-[3.3,.9]))['case_id']]
        return dict(training=train,evaluation=evaluation,disjoint=True,input_hashes=self.hashes,excluded=self.excluded,examples=examples,training_sampling='3 uniformly spaced FRESH per Phase18 run; all26 frozen sudden training cases',evaluation_sampling='10 uniformly spaced FRESH per run +5 uniformly spaced final10s FRESH for failed runs; duplicates deduplicated')

def main():
    OUT.mkdir(exist_ok=True);file=OUT/'manifest.json';assert not file.exists(),'Preserve existing manifest';m=Builder().build();file.write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps({s:{g:sum(c['group']==g for c in m[s]) for g in ('static','sudden')} for s in ('training','evaluation')}))
if __name__=='__main__':main()
