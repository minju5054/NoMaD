"""Four CPU workers shared by overlapping500ms jobs; stream anytime outputs."""
import json,multiprocessing as mp,threading,time,traceback,os
from multiprocessing.connection import wait
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import numpy as np
from nomad_phase20d.recent import RecentSnapshot,build_cache,save_cache
from nomad_phase24r.candidates import CandidateBank
from nomad_phase23.anytime import select_messages
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.evaluate import clean
from .graph import worker,normal_inputs,fan_paths


def archive_planner_files(cache_file,snapshot_file,futures,archive_file):
    """Post-deadline archival only: no solver reads these files afterwards."""
    def work():
        status=dict(cache_file=cache_file,snapshot_file=snapshot_file,derived_cache_removed=False,snapshot_compressed=False)
        try:
            for future in futures:
                try:future.result(timeout=10)
                except BaseException:pass
            if cache_file and os.path.exists(cache_file):os.unlink(cache_file);status['derived_cache_removed']=True
            if snapshot_file and os.path.exists(snapshot_file):
                before=os.path.getsize(snapshot_file);tmp=snapshot_file+'.archive.tmp'
                with np.load(snapshot_file) as z,open(tmp,'wb') as stream:np.savez_compressed(stream,**{key:z[key] for key in z.files})
                os.replace(tmp,snapshot_file);status.update(snapshot_compressed=True,before_bytes=before,after_bytes=os.path.getsize(snapshot_file))
        except BaseException as exc:status['archive_error']=repr(exc)
        with open(archive_file,'w') as stream:json.dump(status,stream)
    threading.Thread(target=work,daemon=True,name='phase24r-planner-archive').start()

def solve_job(pool,job,emit):
    case=job['case'];motion=job['prediction'];B=np.asarray(motion['B_pred']);start=job['dispatch_ns'];deadline=start+500_000_000;payloads=[];messages=[];latest={};receivers={};futures=[];bank=None;cache_info=None;selection_info=None;cache_file=None
    def output(final=False):
        alternatives=bank.alternatives() if bank is not None else [];selection=alternatives[0] if alternatives else None
        result=dict(accepted=selection is not None,output_type=selection['output_type'] if selection else 'STOP',poses=selection['poses'] if selection else None,path=selection['path'] if selection else None,dt=selection['dt'] if selection else None,
            B_pred=B.tolist(),compute_s=(time.monotonic_ns()-start)/1e9,
            dispatch_ns=start,deadline_ns=deadline,worker_done_ns=time.monotonic_ns(),selected=selection,alternatives=alternatives,late_results_used=False,**(bank.statistics() if bank is not None else {}))
        if final:result.update(anytime_messages=messages,mode=job['mode'],prediction=motion,cache_info=cache_info,selection_info=selection_info,return_line=job.get('return_line'))
        return result
    last_signature=None
    try:
        field=RecentSnapshot.load(case['snapshot_file']);strict,cache_info=build_cache(field,case['tick']);cache_file=case['snapshot_file'].replace('snapshot_','cache_');save_cache(field,strict,cache_file);bank=CandidateBank(B,field,strict,deadline);mode=job['mode'];u=job.get('u_ref')
        if mode=='NORMAL':
            selected=normal_inputs(case,B,field);reference=selected['reference'];sigma=selected['sigma'];starts=selected['starts'];selection_info=dict(selected_sample=selected['selected_sample'],all_unsafe=selected['all_unsafe'],names=selected['names'],reference=reference.tolist())
        else:
            reference=np.repeat(B[None,:2],11,axis=0);sigma=1.;starts=fan_paths(B,u)
        candidates=np.asarray([reference]);weights=dict(mode=mode,u_ref=u)
        if mode=='DETOUR':weights['return_line']=job['return_line']
        if time.monotonic_ns()<deadline:
            for i,path in enumerate(starts):
                payload=dict(index=i,B=B.tolist(),v0=motion['previous_vw'][0],candidates=candidates,sigma=sigma,path=path,weights=weights,deadline_ns=deadline,snapshot_file=cache_file)
                receive,send=mp.Pipe(duplex=False);future=pool.submit(worker,payload,send);futures.append(future);receivers[receive]=i
                future.add_done_callback(lambda _,s=send:s.close())
        while receivers:
            remaining=(deadline-time.monotonic_ns())/1e9
            if remaining<=0:break
            for connection in wait(list(receivers),timeout=remaining):
                try:message=connection.recv()
                except EOFError:connection.close();receivers.pop(connection,None);continue
                received=time.monotonic_ns();message['received_ns']=received
                if received>deadline or message['published_ns']>deadline:continue
                if message['kind']=='ERROR':raise RuntimeError(message['error']+'\n'+message['traceback'])
                messages.append(message);latest[message['index']]={**latest.get(message['index'],{}),**message};bank.ingest(message)
                if time.monotonic_ns()>deadline:break
                result=output();s=result['selected'];signature=(result['output_type'],s.get('index'),s.get('ready_ns'),s.get('cost')) if s else ('STOP',)
                if signature!=last_signature:emit(dict(kind='UPDATE',job_id=job['job_id'],result=result));last_signature=signature
                if message['kind']=='DONE':connection.close();receivers.pop(connection,None)
        result=output(True);emit(dict(kind='FINAL',job_id=job['job_id'],result=result))
    except BaseException as exc:emit(dict(kind='ERROR',job_id=job['job_id'],error=repr(exc),traceback=traceback.format_exc()))
    finally:
        for connection in receivers:connection.close()
        for f in futures:f.cancel()
        if cache_file is not None:
            archive_planner_files(cache_file,case['snapshot_file'],futures,case['snapshot_file'].replace('snapshot_','archive_').replace('.npz','.json'))


def main():
    import sys,os
    lock=threading.Lock()
    def emit(value):
        with lock:print(json.dumps(clean(value)),flush=True)
    ctx=mp.get_context('spawn');queue=ctx.Queue()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool,ThreadPoolExecutor(max_workers=8) as jobs:
        futures=[pool.submit(ping) for _ in range(4)];pids=[queue.get(timeout=90) for _ in range(4)]
        for f in futures:f.result()
        emit(dict(kind='READY',pids=pids,coordinator_pid=os.getpid()))
        for line in sys.stdin:
            job=json.loads(line)
            if job is None:break
            jobs.submit(solve_job,pool,job,emit)
if __name__=='__main__':main()
