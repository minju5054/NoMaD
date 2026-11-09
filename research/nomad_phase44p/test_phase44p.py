import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from nomad_isaac.common import sha256_file
from nomad_isaac.old_rollout_placement import magenta_mask
from . import appearance,config,campaign,launch,report


class Tests(unittest.TestCase):
    def test_unique_panels_floor_uvs_and_geometry_signature(self):
        hashes=[]
        for name in appearance.PANELS:
            file=appearance.ASSETS/(name+'.png');hashes.append(sha256_file(file))
            with Image.open(file) as im:self.assertFalse(magenta_mask(np.asarray(im)).any())
        self.assertEqual(len(set(hashes)),14)
        floor=np.asarray(Image.open(appearance.ASSETS/'Floor.png'))
        self.assertEqual(len(np.unique(floor[0],axis=0)),20)
        uv=np.asarray(appearance.cube_uvs());self.assertEqual(uv.shape,(24,2))
        np.testing.assert_array_equal(uv[:4,0],appearance.VERTICES[:4,0]+.5)
        attrs={'xformOp:scale':[10.,3.,.1],'size':1.}
        class Attr:
            def __init__(self,n):self.n=n
            def GetName(self):return self.n
            def Get(self,*a):return attrs[self.n]
            def GetTimeSamples(self):return []
        prim=SimpleNamespace(GetPath=lambda:'/World/Floor',GetTypeName=lambda:'Cube',GetAttributes=lambda:[Attr(n) for n in attrs])
        stage=SimpleNamespace(Traverse=lambda:[prim]);before=appearance.geometry_signature(stage,None)
        attrs['primvars:st']=appearance.cube_uvs()
        self.assertEqual(before,appearance.geometry_signature(stage,None))
        attrs['xformOp:scale']=[10.1,3.,.1]
        self.assertNotEqual(before,appearance.geometry_signature(stage,None))

    def test_six_frozen_configs_launcher_and_preparation_stage_no_execution(self):
        from nomad_phase43p.config import runtime_config as parent
        class Boundary(Exception):pass
        plan=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(plan),6)
        for j in plan:
            c=config.runtime_config(j['method'],j['index'],90,j['scene'],maps_required=False)
            before=parent(j['method'],j['index'],90,j['scene']);skip={'phase44p','topomap_manifest','topomap_manifest_sha256'}
            self.assertEqual({k:v for k,v in c.items() if k not in skip},{k:v for k,v in before.items() if k not in skip})
            self.assertEqual(c['obstacles'],[])
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process')))
            fn.__globals__['verify']=config.verify
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        code='''
from contextlib import nullcontext
from unittest.mock import patch
from nomad_phase44p import campaign as c
from nomad_phase44p.config import RUN_ROOT
calls=[];p=c.protocol()
def halt(root,smoke):
 assert calls==['topomap']
 assert len(c.frozen.base.jobs(root))==6 and not smoke
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('PREP_THEN_SIX_NO_EXECUTION')
c.frozen.base.campaign=halt
with patch.object(c,'exclusive_batch',return_value=nullcontext()),patch.object(c,'verify',return_value=p),patch('nomad_phase44p.topomaps.ensure',side_effect=lambda:calls.append('topomap')):
 c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-1800:]);self.assertIn('PREP_THEN_SIX_NO_EXECUTION',r.stdout)

    def test_generated_reference_seal_rejects_pose_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=copy.deepcopy(config.protocol());seals={}
            for scene in config.SCENES:
                oldpath=Path(p['scenes'][scene]['original_topomap']);old=json.loads(oldpath.read_text())
                folder=root/'topomap'/scene/'topomap';folder.mkdir(parents=True)
                m=copy.deepcopy(old)
                # Use the existing reference images only as a hash-test fixture.
                for n in m['nodes']:n['rgb_file']=str(oldpath.parent/n['rgb_file'])
                path=folder/'manifest.json';path.write_text(json.dumps(m));p['scenes'][scene]['topomap']=str(path)
                record=folder.parent/'render_complete.json';record.write_text(json.dumps(dict(passed=True,geometry_identical=True,example_depth_max_error_m=0.)))
                seals[scene]=dict(manifest_sha256=sha256_file(path),render_complete_sha256=sha256_file(record))
            seal=root/'topomaps_sealed.json';seal.write_text(json.dumps(dict(protocol_sha256=sha256_file(config.HERE/'protocol.json'),scenes=seals)))
            with patch.object(config,'RUN_ROOT',root):config.verify_maps(copy.deepcopy(p))
            file=Path(p['scenes']['L2']['topomap']);m=json.loads(file.read_text());m['nodes'][0]['world_pose'][0]+=.01;file.write_text(json.dumps(m))
            seals['L2']['manifest_sha256']=sha256_file(file);seal.write_text(json.dumps(dict(protocol_sha256=sha256_file(config.HERE/'protocol.json'),scenes=seals)))
            with patch.object(config,'RUN_ROOT',root),self.assertRaises(AssertionError):config.verify_maps(p)

    def test_tables_and_two_example_files(self):
        baseline=json.loads((config.OUT/'preparation/baselines.json').read_text())
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.protocol()['main_order']):
                r=dict(j,technical_validation='PASS',success=True,wrong_stop=False,collision=False,stop_distance_m=.2,node_errors=[])
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'results',root/'report.md',baseline,render_examples=False)
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            self.assertEqual(json.loads((root/'results/analysis.json').read_text())['completed'],6)
            for scene in config.SCENES:
                folder=root/'topomap'/scene;folder.mkdir(parents=True)
                for k,value in [('original',40),('changed',150)]:Image.new('RGB',(320,240),(value,value,value)).save(folder/f'render_{k}.png')
            report.examples(root,root/'figures')
            self.assertEqual(len(list((root/'figures').glob('*.png'))),2)


if __name__=='__main__':unittest.main()
