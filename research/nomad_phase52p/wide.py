"""Saved RGB/NoMaD only; oracle geometry is used solely for this analysis."""
import argparse,csv,json,shutil
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world
from nomad_isaac.clearance import segment_clearance
from nomad_phase31p.report import table
from nomad_phase32o.evaluate import save,csvout

OUT=ROOT/'research/results/phase52p/wide';DOC=ROOT/'docs/PHASE51P_WIDE_ANALYSIS.md'

def read_lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]

def boxes(summary):
    dynamic=summary.get('dynamic_obstacle') or {}
    if dynamic.get('boxes') is not None:return dynamic['boxes']
    return [dynamic] if dynamic.get('spawn') else []

def crossing_points(path,axis,plane):
    output=[]
    for a,b in zip(path[:-1],path[1:]):
        delta=b[axis]-a[axis]
        if delta>1e-12 and a[axis]<=plane<=b[axis]:output.append(a+(plane-a[axis])/delta*(b-a))
    return output

def sample_metrics(sample,pose,box,axis,bounds):
    world=local_to_world(sample,pose);path=np.vstack([np.asarray(pose)[:2],world]);center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2
    low,high=center-half,center+half;lat=1-axis;left_sign=1 if axis==0 else -1;radius=.09;margin=.025
    endpoint=world[-1];relative=left_sign*(endpoint[lat]-center[lat]);width=half[lat]
    side='LEFT' if relative>width else 'RIGHT' if relative<-width else 'BOX_LATERAL_SPAN'
    front=crossing_points(path,axis,low[axis]);far=crossing_points(path,axis,high[axis]+radius)
    gap_lo,gap_hi=bounds
    def in_gap(q):return bool(gap_lo+radius+margin<=q[lat]<=gap_hi-radius-margin and abs(q[lat]-center[lat])>=width+radius+margin)
    clearance=min(segment_clearance(a,b,low,high,radius)[0] for a,b in zip(path[:-1],path[1:]))
    # Inspect the polyline within the box longitudinal slab, including both
    # slab cuts, so a diagonal jump through the box cannot count as a gap.
    slab=[q for q in path if low[axis]<=q[axis]<=high[axis]+radius]+front+far
    slab_gap=bool(slab and all(in_gap(q) for q in slab))
    enter=bool(front and any(in_gap(q) for q in front) and clearance>=margin)
    passes=bool(enter and far and any(in_gap(q) for q in far) and slab_gap)
    forward=float(endpoint[axis]-pose[axis]);backward=forward<0
    return dict(endpoint_world_xy=endpoint.tolist(),endpoint_box_forward_m=float(endpoint[axis]-center[axis]),
        endpoint_box_left_m=float(relative),endpoint_side=side,endpoint_forward_from_robot_m=forward,
        backward_scene_direction=bool(backward),backward_robot_heading=bool(sample[-1,0]<0),
        enters_front_gap=enter,clears_far_gap=passes,target_box_path_clearance_m=float(clearance))

def analyze(output=OUT,document=DOC):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);hashes={}
    source=ROOT/'research/results/phase51p/runs.json';hashes[str(source)]=sha256_file(source)
    runs=[r for r in json.loads(source.read_text()) if r.get('condition')=='WIDE'];events=[];samples=[];coverage=[];images=[]
    definitions=[dict(item='대상',value='Phase51-P WIDE 저장 로그만. 실제 상자가 등장한 뒤, 로봇 중심이 앞면 이전이며 전진축 간격0~1.5m인 모든 추론×상자. H2 두 상자는 따로 집계'),
        dict(item='좌우',value='상자 중심 기준: +x 진행 장면은+y가 왼쪽,H1 +y 진행은-x가 왼쪽. 끝점 좌우/상자 폭 안을 모두 기록'),
        dict(item='틈 진입',value='원 sample+관측pose 연결선이 앞면을 전진 방향으로 통과;상자 footprint clearance>=0.025m이고 교차점이 벽과 로봇반경+0.025m 이상 떨어진 틈'),
        dict(item='완전 통과',value='틈 진입 조건+뒷면을 로봇반경까지 넘어감+상자 전후 slab 내 경로 전체가 동일한 free 측방 범위. 짧은 후보는 진입/완전 통과를 분리'),
        dict(item='되돌아감',value='끝점의 장면 진행축 변위<0. 원 로봇 heading 기준 뒤쪽 여부도 별도 열'),
        dict(item='그림',value='결과 선택 없이 H1,H2,L2 순서로 각 첫 보존 RGB가 있는 적격 추론(낮은seed,추론ID,상자번호). 원 PNG를 그대로 복사;새 렌더/추론 없음'),
        dict(item='한계',value='oracle는 분석만. 경로 수준 기하이며 제어/NoMaD 재생성 후 주행 성공을 뜻하지 않음. SLW/LC는 돌발 상자가 없어 해당 사건 없음')]
    for r in sorted(runs,key=lambda r:(r['base_scene'],r['index'])):
        root=Path(r['output']);scene=r['base_scene'];axis=1 if scene=='H1' else 0
        if r['technical_validation']!='PASS':coverage.append(dict(scene=scene,seed=r['index'],status='TECHNICAL_FAILURE',eligible=0));continue
        sf=root/'summary.json';cf=root/'scenario.json';inf=root/'model/inference.jsonl'
        for f in (sf,cf,inf):hashes[str(f)]=sha256_file(f)
        summary=json.loads(sf.read_text());c=json.loads(cf.read_text());bs=boxes(summary);n=0;image_n=0
        for e in read_lines(inf):
            pose=np.asarray(e['observation_pose']);t=e['observation_sim_s']
            for number,b in enumerate(bs,1):
                spawn=b['spawn'];box=spawn['obstacle'];front=box['center_xy_m'][axis]-box['size_xyz_m'][axis]/2
                distance=front-pose[axis]
                if t<spawn['simulation_time_s'] or not 0<=distance<=1.5:continue
                file=root/'model/derived'/f"{e['id']:04d}.npz";hashes[str(file)]=sha256_file(file)
                with np.load(file,allow_pickle=False) as z:metric=z['metric'].copy()
                assert metric.shape==(8,8,2) and np.isfinite(metric).all()
                key=dict(scene=scene,seed=r['index'],inference_id=e['id'],box_number=number,observation_s=t,observation_pose=pose.tolist(),front_axial_distance_m=float(distance))
                results=[dict(**key,sample=i,**sample_metrics(p,pose,box,axis,c['phase51p_wide']['available_bounds_m'])) for i,p in enumerate(metric)]
                samples.extend(results)
                row=dict(**key,samples=8,enters_front_gap=sum(x['enters_front_gap'] for x in results),clears_far_gap=sum(x['clears_far_gap'] for x in results),backwards=sum(x['backward_scene_direction'] for x in results),
                    left_endpoints=sum(x['endpoint_side']=='LEFT' for x in results),right_endpoints=sum(x['endpoint_side']=='RIGHT' for x in results),rgb_file=str(root/e['rgb_file']))
                exists=Path(row['rgb_file']).exists();row['rgb_retained']=exists;events.append(row);n+=1;image_n+=exists
        coverage.append(dict(scene=scene,seed=r['index'],status='AVAILABLE' if bs else 'NO_SPAWNED_BOX',boxes=len(bs),eligible=n,rgb_available=image_n))
    stats=[]
    for scene in ('H1','H2','L2','SLW','LC','ALL'):
        group=[e for e in events if scene=='ALL' or e['scene']==scene];den=8*len(group)
        stats.append(dict(scene=scene,inference_box_events=len(group),samples=den,
            front_gap_fraction=sum(e['enters_front_gap'] for e in group)/den if den else None,
            full_gap_fraction=sum(e['clears_far_gap'] for e in group)/den if den else None,
            backward_fraction=sum(e['backwards'] for e in group)/den if den else None,
            left_endpoint_fraction=sum(e['left_endpoints'] for e in group)/den if den else None,
            right_endpoint_fraction=sum(e['right_endpoints'] for e in group)/den if den else None))
    image_folder=ROOT/'docs/images/phase52p_wide';image_folder.mkdir(parents=True,exist_ok=True)
    for scene in ('H1','H2','L2'):
        eligible=sorted([e for e in events if e['scene']==scene and e['rgb_retained']],key=lambda e:(e['seed'],e['inference_id'],e['box_number']))
        if not eligible:continue
        e=eligible[0];original=Path(e['rgb_file']);dest=image_folder/f"{scene}_{e['seed']}_{e['inference_id']:04d}.png";shutil.copyfile(original,dest)
        assert sha256_file(dest)==sha256_file(original);hashes[str(original)]=sha256_file(original)
        images.append(dict(scene=scene,seed=e['seed'],inference_id=e['inference_id'],observation_s=e['observation_s'],source=str(original),file=str(dest.relative_to(ROOT)),sha256=sha256_file(dest)))
    for name,data in [('events',events),('samples',samples),('summary',stats),('coverage',coverage)]:csvout(output/(name+'.csv'),data)
    save(output/'input_hashes.json',hashes);save(output/'images.json',images)
    save(output/'analysis.json',dict(saved_runs=len(runs),inference_box_events=len(events),samples=len(samples),images=len(images),simulations=0,new_inferences=0))
    doc='# Phase51-P WIDE: 저장 NoMaD 후보 분석\n\n'+table(definitions)+'\n\n'+table(stats)+'\n\n'+table(coverage)+'\n'
    for e in images:doc+=f"\n### {e['scene']} seed {e['seed']}, inference {e['inference_id']}, {e['observation_s']:.3f}s\n\n![보존 RGB](images/phase52p_wide/{Path(e['file']).name})\n"
    Path(document).write_text(doc);print(json.dumps(dict(events=len(events),samples=len(samples),images=len(images))))

if __name__=='__main__':analyze()
