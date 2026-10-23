"""Dedicated CPU process. GraphV4 unchanged; one v5 solve per request."""
import json
import sys
import time
import traceback
from .config import protocol
from .graph_v5 import GraphV5, SignedDistanceField


def main():
    p=protocol()['graph_parameters'];fields={}
    print(json.dumps({'kind':'ready'}),flush=True)
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop':return
        start=time.monotonic_ns();r={'job_id':job['job_id'],'id':job['id'],'worker_start_ns':start}
        stage='initialization'
        try:
            key=json.dumps(job['public_config']['obstacles'],sort_keys=True)
            if key not in fields:fields[key]=SignedDistanceField(job['public_config'],p['sdf_resolution_m'],p['sdf_padding_m'])
            g=GraphV5(job['world_xy'],job['boundary'],job['previous_command'],job['public_config'],p,fields[key],job.get('previous_xy'))
            stage='solve'
            poses,profile,solver=g.solve()
            r.update(kind='result',poses=poses.tolist(),speed_profile=profile,solver=solver,accepted=solver['feasible'])
        except Exception as e:r.update(kind='result',accepted=False,initialization_rejected=stage=='initialization',failure_stage=stage,error=repr(e),traceback=traceback.format_exc())
        r['worker_end_ns']=time.monotonic_ns();print(json.dumps(r),flush=True)

if __name__=='__main__':main()
