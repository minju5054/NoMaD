"""Visualization-only regression coverage; synthetic files, no navigation."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from . import visualize as v
from .report import render


def fixture(path,method):
    path.mkdir()
    for f in v.REQUIRED:
        p=path/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('')
    (path/'summary.json').write_text(json.dumps(dict(epoch_monotonic_ns=1)))
    (path/'agent_trajectory.csv').write_text('simulation_time_s,x_m,y_m,yaw_rad\n0,0,0,0\n0.1,0.01,0,0\n')
    (path/'phase20_commands.jsonl').write_text(json.dumps(dict(time_s=0,source='STOP_WAIT',path_source_id=None))+'\n')
    (path/'observations.jsonl').write_text(json.dumps(dict(observation_id=0,observation_sim_s=0,rgb_file='rgb.png'))+'\n')
    Image.new('RGB',(8,8)).save(path/'rgb.png')
    return dict(scene='L3',index=87,method=method,output=str(path),classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False)


class Tests(unittest.TestCase):
    def test_missing_summary_log_and_rgb(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixture(Path(d)/'run','M3_DETOUR');root=Path(r['output'])
            self.assertIsNotNone(v.load(r))
            for name in ('summary.json','phase20_commands.jsonl','rgb.png'):
                f=root/name;content=f.read_bytes();f.unlink();issues=[]
                self.assertIsNone(v.load(r,issues));self.assertIn(name,issues[0]['reason']);f.write_bytes(content)
    def test_one_missing_panel_all_three_figures(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);good=fixture(root/'good','M1_ROTATE');bad=fixture(root/'bad','M3_DETOUR');(root/'bad/summary.json').unlink()
            with patch.object(v,'scene_levels'),patch.object(v,'blank_panel',wraps=v.blank_panel) as blank:
                status=v.generate([good,bad],root/'out',cases=[('L3',87)])
            self.assertFalse(status[0]['skipped']);self.assertEqual(blank.call_count,8)
            for name in ('drive_L3_87.png','drive_L3_87.gif','rgb_strip_L3_87.png'):self.assertTrue((root/'out'/name).is_file())
            self.assertEqual(status[0]['missing'][0]['method'],'M3_DETOUR')
    def test_both_missing_skips_and_reports_reason(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);records=[]
            for i,m in enumerate(v.COLORS):
                r=fixture(root/str(i),m);(Path(r['output'])/'summary.json').unlink();records.append(r)
            data={m:None for m in v.COLORS}
            for function in (v.pair_plot,v.pair_gif,v.rgb_strip):self.assertFalse(function('L3',87,data,root))
            with patch.object(v,'scene_levels'):render(records,root/'out',root/'report.md',make_figures=True)
            self.assertFalse(list((root/'out').glob('*.png')));self.assertFalse(list((root/'out').glob('*.gif')))
            report=(root/'report.md').read_text();self.assertIn('All seed figures skipped (both runs unavailable)',report)
            self.assertIn('Missing required files: summary.json',report);self.assertNotIn('drive_L3_87.',report)

if __name__=='__main__':unittest.main()
