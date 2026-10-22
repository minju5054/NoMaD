"""One external CPU process; unchanged Graph v4, one solve per request."""
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
from nomad_phase0.graph_v4 import GraphV4, SignedDistanceField


def main():
    p=json.loads(Path(__file__).parents[1].joinpath('nomad_phase0/graph_v4_protocol.json').read_text())
    fields={}
    print(json.dumps({'kind':'ready'}),flush=True)
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop': return
        start=time.monotonic_ns(); response={'job_id':job['job_id'],'id':job['id'],'worker_start_ns':start}
        try:
            key=json.dumps(job['public_config']['obstacles'],sort_keys=True)
            if key not in fields:
                fields[key]=SignedDistanceField(job['public_config'],p['sdf_resolution_m'],p['sdf_padding_m'])
            graph=GraphV4(job['world_xy'],job['boundary'],job['previous_command'],job['public_config'],p,
                          fields[key],job.get('previous_xy'))
            poses,solver=graph.solve()
            response.update(kind='result',poses=poses.tolist(),solver=solver,
                accepted=solver['feasible'],sdf_build_s=fields[key].build_wall_s)
        except Exception as e:
            response.update(kind='result',accepted=False,initialization_rejected=True,
                error=repr(e),traceback=traceback.format_exc())
        response.update(worker_end_ns=time.monotonic_ns())
        print(json.dumps(response),flush=True)

if __name__=='__main__':main()
