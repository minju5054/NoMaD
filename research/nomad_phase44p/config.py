import json,copy
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase43p.config import runtime_config as frozen_config,verify as verify43,INDICES,METHODS

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase44p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase44p_01'
SCENES=('L2','H2')


def protocol():return json.loads((HERE/'protocol.json').read_text())


def verify_maps(p):
    seal=json.loads((RUN_ROOT/'topomaps_sealed.json').read_text())
    assert seal['protocol_sha256']==sha256_file(HERE/'protocol.json')
    for scene in SCENES:
        new=Path(p['scenes'][scene]['topomap']);item=seal['scenes'][scene]
        assert sha256_file(new)==item['manifest_sha256']
        record=new.parent.parent/'render_complete.json'
        assert sha256_file(record)==item['render_complete_sha256']
        check=json.loads(record.read_text());assert check['passed'] and check['geometry_identical'] and check['example_depth_max_error_m']<=1e-6
        m=json.loads(new.read_text());old=json.loads(Path(p['scenes'][scene]['original_topomap']).read_text())
        assert m['dynamic_obstacle'] is False and len(m['nodes'])==m['node_count']==old['node_count']
        assert m['spacing_sim_s']==old['spacing_sim_s']
        for a,b in zip(m['nodes'],old['nodes']):
            for k in ('node_id','reference_pose_row','world_pose','simulation_time_s'):assert a[k]==b[k],(scene,k)
            assert sha256_file(new.parent/a['rgb_file'])==a['png_sha256']
        p['scenes'][scene]['topomap_sha256']=item['manifest_sha256']
    return p


def verify(require_maps=False):
    verify43();p=protocol();assert p['status']=='FROZEN' and len(p['main_order'])==6
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    if require_maps:p=verify_maps(p)
    return p


def runtime_config(method,index,timeout=90,level='L2',maps_required=True):
    assert level in SCENES and index in INDICES
    c=frozen_config(method,index,timeout,level);p=verify(require_maps=maps_required)
    c.update(phase44p=True,topomap_manifest=p['scenes'][level]['topomap'],topomap_manifest_sha256=p['scenes'][level]['topomap_sha256'])
    return c
