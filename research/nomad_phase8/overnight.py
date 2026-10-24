"""Serial night orchestration. Each stage exit is recorded; report failure does not hide it."""
import argparse
import datetime
import json
import subprocess
from nomad_isaac.common import ROOT
from .batch import completion

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--status',action='store_true');a=parser.parse_args()
    parent=ROOT.parent/'artifacts/isaac6';journal=parent/'overnight_phase8_9.jsonl'
    phases=[(8,parent/'phase8_combo_rtc_01'),(9,parent/'phase9_sudden_01')]
    if a.status:
        history=[json.loads(x) for x in journal.read_text().splitlines()] if journal.exists() else []
        print(json.dumps(dict(last_stage_event=history[-1] if history else None,phases={str(n):completion(root) for n,root in phases}),ensure_ascii=False));return
    assert not journal.exists() and all(not root.exists() for _,root in phases),'No overwrite/retry'
    with journal.open('x') as log:
        def emit(data):log.write(json.dumps(dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**data))+'\n');log.flush()
        codes=[]
        for n,root in phases:
            for stage in ('batch','report'):
                name=f'phase{n}_{stage}';command=['/usr/bin/python3','-u','-m',f'nomad_phase{n}.{stage}','--run-root',str(root)]
                if stage=='batch':command.append('--execute')
                emit(dict(stage=name,event='START',exit_code=None))
                code=subprocess.call(command,cwd=ROOT);codes.append(code)
                emit(dict(stage=name,event='END',exit_code=code))
        emit(dict(stage='overnight',event='END',exit_code=1 if any(codes) else 0))
    raise SystemExit(1 if any(codes) else 0)
if __name__=='__main__':main()
