"""Read saved post-publication history; never infer a missing observed flag."""
import csv,hashlib,json
from pathlib import Path
from collections import defaultdict
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase32o.evaluate import save,csvout
from nomad_phase37.audit import metadata

OUT=ROOT/'research/results/phase37b';HASHES={}

def register(path):
    path=Path(path).resolve()
    if str(path) not in HASHES:HASHES[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return path

def read(path):return json.loads(register(path).read_text())
def lines(path):return [json.loads(s) for s in register(path).read_text().splitlines() if s] if Path(path).exists() else []

def snapshot(path):
    register(path)
    with np.load(path) as z:
        arrays={key:z[key].copy() for key in ('occupied','observed','new_component_ids','first_free_tick','last_free_tick','first_occupied_tick','origin')}
        arrays.update(h=float(z['h']),radius=float(z['radius']),component_births={int(k):int(v) for k,v in json.loads(str(z['component_births'])).items()})
    return SimpleNamespace(**arrays,metadata=metadata(path))

def common_rows():
    with register(ROOT/'research/results/phase37/triggers.csv').open() as f:rows=list(csv.DictReader(f))
    grouped=defaultdict(list)
    for row in rows:grouped[row['output']].append(row)
    assert len(rows)==4915 and len(grouped)==30
    return grouped

def published_free_witness(observed,occupied,last_free,tick,first_occupied):
    return np.asarray(observed)&~np.asarray(occupied)&(np.asarray(last_free)==tick)&(tick<np.asarray(first_occupied))

def inventory(root):
    updates=lines(root/'depth/updates.jsonl');copies={}
    for f in sorted((root/'repair_jobs').glob('input_*.npz')):
        m=metadata(f);copies[(m['frame_id'],m['sim_s'])]=f
    result=[]
    for u in updates:
        path=Path(u['file']);path=path if path.exists() else copies.get((u['frame_id'],u['sim_s']))
        result.append((round(u['sim_s']*72),path,u))
    result.sort(key=lambda x:x[0]);return result

def build(root,rows):
    files=sorted({r['snapshot_file'] for r in rows});relevant=None;ff=None;fo=None
    for file in files:
        f=snapshot(file);candidate=f.occupied&f.observed&(f.new_component_ids>0)
        assert np.all((f.first_free_tick[candidate]>=0)&(f.first_free_tick[candidate]<f.first_occupied_tick[candidate]))
        if relevant is None:
            relevant=np.zeros(candidate.shape,bool);ff=np.full(candidate.shape,-1,np.int32);fo=ff.copy()
        overlap=relevant&candidate
        np.testing.assert_array_equal(ff[overlap],f.first_free_tick[overlap]);np.testing.assert_array_equal(fo[overlap],f.first_occupied_tick[overlap])
        relevant|=candidate;ff[candidate]=f.first_free_tick[candidate];fo[candidate]=f.first_occupied_tick[candidate]
    indices=np.flatnonzero(relevant);free=ff.ravel()[indices];occupied=fo.ravel()[indices]
    first_confirmed=np.full(len(indices),-1,np.int32)
    first_free_observed=np.full(len(indices),-1,np.int8);first_free_occupied=first_free_observed.copy()
    frames=inventory(root);ticks=np.array([x[0] for x in frames],np.int32);missing=np.array([x[1] is None for x in frames],bool)
    for tick,path,meta in frames:
        if path is None:continue
        register(path)
        with np.load(path) as z:
            observed=z['observed'].ravel()[indices];occ=z['occupied'].ravel()[indices];last=z['last_free_tick'].ravel()[indices]
        evidence=published_free_witness(observed,occ,last,tick,occupied)
        take=evidence&(first_confirmed<0);first_confirmed[take]=tick
        at_first=free==tick;first_free_observed[at_first]=observed[at_first].astype(np.int8);first_free_occupied[at_first]=occ[at_first].astype(np.int8)
    # The first free timestamp already proves a ray update and, since it
    # precedes first occupied, not-occupied at that instant. What it does not
    # prove is observed=True *after* shadow handling in the published map.
    start=np.searchsorted(ticks,free,side='left');end=np.searchsorted(ticks,occupied,side='left')
    prefix=np.r_[0,np.cumsum(missing)];missing_between=prefix[end]-prefix[start]
    timestamps_known=np.isin(free,ticks)&np.isin(occupied,ticks)
    confirmed=first_confirmed>=0
    complete=(missing_between==0)&timestamps_known
    unknown=~confirmed&~complete;rejected=~confirmed&complete
    result=dict(indices=indices,shape=np.array(relevant.shape),first_free_tick=free,first_occupied_tick=occupied,
        first_confirmed_free_tick=first_confirmed,first_free_observed=first_free_observed,first_free_occupied=first_free_occupied,
        missing_frames_before_occupied=missing_between,history_complete=complete,confirmed=confirmed,unknown=unknown,rejected=rejected,
        origin=f.origin,h=np.array(f.h))
    summary=dict(output=str(root),phase=rows[0]['phase'],scene=rows[0]['scene'],index=int(rows[0]['index']),
        common_opportunities=len(rows),candidate_cell_union=len(indices),legacy_ray_provenance_cells=len(indices),
        confirmed_published_free_cells=int(confirmed.sum()),unmeasured_history_cells=int(unknown.sum()),
        no_published_free_with_complete_history_cells=int(rejected.sum()),first_free_frame_observed_false=int((first_free_observed==0).sum()),
        first_free_frame_unavailable=int((first_free_observed<0).sum()),available_history_frames=int((~missing).sum()),published_frames=len(frames))
    return result,summary

def main():
    summaries=[]
    for i,(directory,rows) in enumerate(sorted(common_rows().items())):
        data,s=build(Path(directory),rows);key=f"{s['phase']}_{s['scene']}_{s['index']}";folder=OUT/'evidence';folder.mkdir(parents=True,exist_ok=True)
        path=folder/(key+'.npz');assert not path.exists(),path;np.savez_compressed(path,**data)
        summaries.append(s);print('[history]',i+1,'/30',key,flush=True)
    save(OUT/'evidence_summary.json',summaries);csvout(OUT/'evidence_summary.csv',summaries);save(OUT/'history_input_hashes.json',HASHES)
    print(json.dumps({k:sum(r[k] for r in summaries) for k in ('candidate_cell_union','confirmed_published_free_cells','unmeasured_history_cells','no_published_free_with_complete_history_cells','first_free_frame_observed_false','first_free_frame_unavailable')}))

if __name__=='__main__':main()
