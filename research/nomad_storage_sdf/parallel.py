"""Process-parallel, fail-stop continuation of the verified storage retrofit.

Only storage tools change. Workers own disjoint files and durable journals;
each replacement is byte-verified and globally serialized against aborts.
"""
import argparse, hashlib, json, multiprocessing as mp, os, signal, subprocess, threading, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from pathlib import Path
from . import bulk as b
from . import profiled
from .bulk_guard import Guard

TERMINAL={'CONVERTED','ALREADY_COMPACT','SKIPPED_SDF_MISMATCH','SKIPPED_DIFFERENT_FORMAT','SKIPPED_UNKNOWN_VERSION'}
CTX={}

class Aborted(RuntimeError):pass

def memory(pids=()):
    mem={k:int(v.split()[0])*1024 for k,v in (s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())}
    vm=dict(s.split() for s in Path('/proc/vmstat').read_text().splitlines())
    rss=0
    for pid in pids:
        try:
            lines=Path(f'/proc/{pid}/status').read_text().splitlines()
            rss+=sum(int(s.split()[1])*1024 for s in lines if s.startswith('VmRSS:'))
        except (FileNotFoundError,ProcessLookupError):pass
    return dict(epoch=time.time(),available_bytes=mem['MemAvailable'],system_used_bytes=mem['MemTotal']-mem['MemAvailable'],
                swap_used_bytes=mem['SwapTotal']-mem['SwapFree'],swap_out_pages=int(vm['pswpout']),swap_in_pages=int(vm['pswpin']),worker_rss_bytes=rss)

def memory_pressure(now,baseline):
    # Previously swapped-out idle pages are reported separately; detect new use.
    return now['available_bytes']<4*1024**3 or now['swap_used_bytes']>baseline['swap_used_bytes'] or now['swap_out_pages']>baseline['swap_out_pages']

def init_worker(ids,ready,start,registry,abort,mutation_lock,cpus,isaac,protected_roots=('phase32_01',)):
    index=ids.get();registry[index]=os.getpid();os.sched_setaffinity(0,set(cpus))
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<10:os.nice(10-priority)
    ready.put((index,os.getpid()));start.wait()
    b.ISAAC=Path(isaac)
    guard=Guard(b.ISAAC,protected_roots=protected_roots);guard.ignore.update(pid for pid in registry if pid)
    CTX.update(index=index,abort=abort,lock=mutation_lock,guard=guard)

def ping():return os.getpid()

def check_abort():
    if CTX['abort'].is_set():raise Aborted('Another worker failed; no further replacement')

class CommitGuard:
    def assert_clear(self,root):
        check_abort();CTX['guard'].assert_clear(root)

def worker_file(job):
    path,backup,version,entry,prior,root,folder=job;started=time.monotonic();check_abort();timer=profiled.Timer()
    log=Path(folder)/'workers'/f"worker_{CTX['index']:02d}_{os.getpid()}.jsonl";log.parent.mkdir(parents=True,exist_ok=True)
    try:
        with timer.stage('guard'):CTX['guard'].assert_clear(Path(root))
        row=profiled.prepare(path,version,prior,timer)
        row.update(worker_id=CTX['index'],worker_pid=os.getpid(),nice=os.getpriority(os.PRIO_PROCESS,0),verified_at_utc=datetime.now(timezone.utc).isoformat())
        # The shared lock makes observing an error and starting a replacement
        # mutually exclusive; all expensive work remains process-parallel.
        with timer.stage('lock_wait'):CTX['lock'].acquire()
        try:
            check_abort()
            with log.open('a') as f:
                raw_record=b.journal_writer(f)
                def record(value):
                    with timer.stage('manifest'):raw_record(value)
                row=profiled.commit(row,CommitGuard(),Path(root),record,timer)
                row.update(worker_seconds=time.monotonic()-started,finished_epoch=time.time())
                row['timings_s']=dict(timer.seconds)
                record(row)
        finally:CTX['lock'].release()
        row['worker_seconds']=time.monotonic()-started
        timer.seconds['other']=max(0.,row['worker_seconds']-sum(timer.seconds.values()))
        row['timings_s']=dict(timer.seconds)
        return row
    except (Aborted,b.OperatorAbsent):raise
    except BaseException as exc:
        with CTX['lock']:CTX['abort'].set()
        with log.open('a') as f:
            b.journal_writer(f)(dict(status='ERROR',path=str(path),worker_pid=os.getpid(),error=repr(exc),epoch=time.time(),timings_s=timer.seconds))
        raise

def merged_rows(folder):
    folder=Path(folder);rows={r['path']:r for r in b.read_jsonl(folder/'manifest.jsonl')}
    for file in [folder/'journal.jsonl',*sorted((folder/'workers').glob('*.jsonl'))]:
        records=b.read_jsonl(file);latest={}
        for row in records:
            if row['status'] in TERMINAL or row['status']=='PREPARED':latest[row['path']]=row
        for path,row in latest.items():
            if row['status']=='PREPARED':
                actual=b.sha(path)
                if actual==row['new_sha256']:
                    b.validate_compact(row);row=dict(row,status='CONVERTED')
                elif actual==row['original_sha256']:continue
                else:raise RuntimeError('Unreconciled interrupted worker replacement: '+path)
            if path in rows and rows[path]['new_sha256']!=row['new_sha256']:raise RuntimeError('Conflicting worker manifests: '+path)
            rows[path]=row
    return rows

def unique_jobs(paths):
    resolved=[str(Path(p).resolve()) for p in paths]
    if len(set(resolved))!=len(resolved):raise ValueError('Duplicate file ownership')
    return resolved

class Runner:
    def __init__(self,plan,baseline,initial,workers):
        self.plan=plan;self.baseline=baseline;self.initial=initial;self.workers=workers
        self.context=mp.get_context('spawn');self.abort=self.context.Event();self.mutation_lock=self.context.Lock()
        self.pool=None;self.pids=[];self.guard=Guard(b.ISAAC,protected_roots=plan.get('protected_roots',('phase32_01',)));self.original_ignore=set(self.guard.ignore)
        self.throttle=threading.Event();self.done=threading.Event();self.stats_lock=threading.Lock()
        self.started=time.monotonic();self.processed=0;self.converted=0;self.saved=0;self.last_save=0;self.peak=memory()
        self.profiles={};self.benchmark_id=plan.get('benchmark_id','parallel')
        self.state=dict(status='RUNNING',mode='PROCESS_PARALLEL',pid=os.getpid(),start_utc=datetime.now(timezone.utc).isoformat(),start_epoch=time.time(),
                        workers=workers,nice=os.getpriority(os.PRIO_PROCESS,0),stage='starting',completed_roots=[],parallel_processed=0,
                        remaining_at_transition=baseline['remaining_candidates'],initial_processed=initial,baseline_memory=dict(self.peak),worker_changes=[])
        self.monitor=threading.Thread(target=self.monitor_memory,daemon=True);self.monitor.start()
    def monitor_memory(self):
        try:
            with (b.OUT/'memory_samples.jsonl').open('a') as f:
                while not self.done.is_set():
                    now=memory(self.pids)
                    with self.stats_lock:
                        for key in ('system_used_bytes','swap_used_bytes','worker_rss_bytes'):self.peak[key]=max(self.peak[key],now[key])
                        self.peak['available_bytes']=min(self.peak['available_bytes'],now['available_bytes'])
                    if memory_pressure(now,self.state['baseline_memory']):self.throttle.set()
                    f.write(json.dumps(dict(now,workers=self.workers))+'\n');f.flush()
                    self.done.wait(.25)
        except BaseException as exc:
            self.state['monitor_error']=repr(exc);self.abort.set()
    def start_pool(self,n):
        self.workers=n;ids=self.context.Queue();ready=self.context.Queue();start=self.context.Event();registry=self.context.Array('i',n)
        for i in range(n):ids.put(i)
        allowed=sorted(os.sched_getaffinity(0));cpus=[x for x in allowed if x not in (7,15)] or allowed
        self.pool=ProcessPoolExecutor(max_workers=n,mp_context=self.context,initializer=init_worker,
                initargs=(ids,ready,start,registry,self.abort,self.mutation_lock,cpus,str(b.ISAAC),self.plan.get('protected_roots',('phase32_01',))))
        futures=[self.pool.submit(ping) for _ in range(n)]
        try:
            self.pids=[ready.get(timeout=60)[1] for _ in range(n)]
            self.guard.ignore=self.original_ignore|set(self.pids);start.set()
            for f in futures:f.result(timeout=60)
        except BaseException:start.set();self.abort.set();raise
        self.state.update(workers=n,worker_pids=self.pids,worker_cores=cpus);self.persist(force=True)
    def stop_pool(self):
        if self.pool:self.pool.shutdown(wait=True,cancel_futures=True)
        self.pool=None;self.pids=[];self.guard.ignore=set(self.original_ignore)
    def persist(self,force=False):
        elapsed=time.monotonic()-self.started
        if not force and elapsed-self.last_save<1:return
        with self.stats_lock:peaks=dict(self.peak)
        self.state.update(parallel_elapsed_s=elapsed,parallel_processed=self.processed,parallel_converted=self.converted,parallel_saved_bytes=self.saved,memory_peaks=peaks,
                          remaining_candidates=max(0,self.baseline['remaining_candidates']-self.processed))
        b.save(b.OUT/'state.json',self.state);self.last_save=elapsed
        if elapsed>=60 and not (b.OUT/(self.benchmark_id+'_profile_1min.json')).exists():
            stages={k:sum(r['timings_s'][k] for r in self.profiles.values()) for k in profiled.STAGES}
            profile=dict(elapsed_s=elapsed,files=self.processed,workers=list(self.profiles.values()),stage_worker_seconds=stages,
                         one_touch_backup_enabled=False,compression='np.savez_compressed unchanged',verification='all arrays bitwise; no skipped checks')
            b.save(b.OUT/(self.benchmark_id+'_profile_1min.json'),profile);print('[profile 1min]',json.dumps(stages),flush=True)
        if elapsed>=300 and not (b.OUT/(self.benchmark_id+'_5min.json')).exists():
            rate=self.processed/elapsed*60
            measure=dict(elapsed_s=elapsed,processed=self.processed,converted=self.converted,files_per_minute=rate,
                         mean_seconds_per_file=elapsed/self.processed if self.processed else None,
                         remaining_candidates=self.state['remaining_candidates'],eta_seconds=self.state['remaining_candidates']/rate*60 if rate else None,
                         memory_peaks=peaks,baseline_memory=self.state['baseline_memory'],workers=self.workers,worker_changes=self.state['worker_changes'],
                         includes_backup_and_verification=False,includes_verification=True,backup_enabled=False,scope='first 300 seconds including pool startup, verification, and replacements; no backup')
            b.save(b.OUT/(self.benchmark_id+'_5min.json'),measure);print('[5min]',json.dumps(measure),flush=True)
    def batch_run(self,jobs,rows):
        unique_jobs([j[0] for j in jobs]);iterator=iter(jobs);pending={};exhausted=False;pause=False
        while pending or not exhausted:
            if self.abort.is_set():raise RuntimeError('Worker/monitor error; all replacements halted')
            if not pause:
                try:b.require_heartbeat()
                except b.OperatorAbsent:pause=True;exhausted=True
            resize=self.throttle.is_set() and self.workers>8 and not pause
            while not exhausted and not resize and len(pending)<self.workers:
                try:job=next(iterator)
                except StopIteration:exhausted=True;break
                pending[self.pool.submit(worker_file,job)]=job[0]
            if pending:
                done,_=wait(pending,timeout=.25,return_when=FIRST_COMPLETED)
                for f in done:
                    pending.pop(f);row=f.result();rows[row['path']]=row
                    if row['status']!='ALREADY_COMPACT':self.processed+=1
                    if row['status']=='CONVERTED':self.converted+=1
                    key=str(row['worker_pid'])
                    stats=self.profiles.setdefault(key,dict(worker_id=row['worker_id'],pid=row['worker_pid'],files=0,worker_seconds=0.,timings_s={k:0. for k in profiled.STAGES}))
                    stats['files']+=1;stats['worker_seconds']+=row['worker_seconds']
                    for k,v in row['timings_s'].items():stats['timings_s'][k]+=v
                    self.saved+=row['before_bytes']-row['after_bytes'];self.state.update(files_complete=len(rows),last_file=row['path'])
            self.persist()
            if resize and not pending:
                self.state['worker_changes'].append(dict(epoch=time.time(),before=self.workers,after=8,reason='Memory available <4 GiB or new swap usage',memory=memory(self.pids)))
                self.stop_pool();self.start_pool(8);print('[memory] reduced workers to 8',flush=True)
        if pause:raise b.OperatorAbsent('Agent heartbeat expired at a safe file boundary')
    def root(self,entry):
        root=Path(entry['path']);folder=b.ROOT_OUT/root.name;folder.mkdir(parents=True,exist_ok=True)
        if (folder/'summary.json').exists() and b.read(folder/'summary.json').get('status')=='COMPLETE':return b.read(folder/'summary.json')
        reason=self.guard.reason(root,force=True)
        if reason:return dict(root=root.name,status='EXCLUDED_ACTIVE_OR_LOCKED',reason=reason,converted=0)
        rows=merged_rows(folder);prior={r['path']:r for r in b.read(b.ROOT/'research/results/storage_retrofit/manifest.json')}
        for run in entry['runs']:
            b.require_heartbeat();remaining=[p for p in run['files'] if p not in rows]
            if not remaining:continue
            self.guard.assert_clear(root);self.state.update(root=root.name,run=run['path'],stage='convert',files_complete=len(rows),root_target_files=entry['target_files'],backup_enabled=False);self.persist(force=True)
            if not run['version']['supported']:
                for p in remaining:
                    h=b.sha(p);size=Path(p).stat().st_size;rows[p]=dict(path=p,status='SKIPPED_UNKNOWN_VERSION',reason=run['version']['reason'],original_sha256=h,new_sha256=h,before_bytes=size,after_bytes=size)
                b.write_jsonl(folder/'manifest.jsonl',list(rows.values()));continue
            # User explicitly disabled all further One Touch backups. Original
            # SHA/arrays are captured in-worker before any temporary is written.
            b.require_heartbeat()
            jobs=[(p,None,run['version'],None,prior.get(p),str(root),str(folder)) for p in remaining]
            self.batch_run(jobs,rows);b.write_jsonl(folder/'manifest.jsonl',list(rows.values()))
        # Merge durable worker manifests and verify unique ownership before root completion.
        merged=merged_rows(folder)
        if set(merged)!=set(rows):raise RuntimeError('Worker merge coverage differs from coordinator')
        b.write_jsonl(folder/'manifest.jsonl',list(merged.values()));counts=Counter(r['status'] for r in merged.values());tested=[r for r in merged.values() if r.get('values_bit_equal') is not None]
        result=dict(root=root.name,status='COMPLETE',files=len(merged),converted=counts['CONVERTED'],bit_checked=len(tested),bit_equal=sum(r['values_bit_equal'] for r in tested),
                    bit_match_fraction=sum(r['values_bit_equal'] for r in tested)/len(tested) if tested else None,skipped=len(merged)-counts['CONVERTED'],
                    skip_reasons={k:v for k,v in counts.items() if k!='CONVERTED'},before_bytes=entry['before_bytes'],after_bytes=b.folder_bytes(root),
                    saved_bytes=sum(r['before_bytes']-r['after_bytes'] for r in merged.values()),target_before_bytes=sum(r['before_bytes'] for r in merged.values()),
                    target_after_bytes=sum(r['after_bytes'] for r in merged.values()),manifest=str(folder/'manifest.jsonl'),manifest_sha256=b.sha(folder/'manifest.jsonl'),
                    df=subprocess.check_output(['df','-B1',str(b.ISAAC),self.plan['backup_directory']],text=True))
        b.save(folder/'summary.json',result);print('[root done]',root.name,counts,flush=True);return result
    def run(self):
        try:
            self.start_pool(self.workers)
            for entry in self.plan['roots']:
                if entry['status'] in ('NO_TARGET_FILES','EXCLUDED_ACTIVE_OR_LOCKED'):continue
                result=self.root(entry);self.state['completed_roots'].append(result);self.persist(force=True)
            self.state.update(status='COMPLETE',stage='finished',pid=None)
        except b.OperatorAbsent as exc:self.state.update(status='PAUSED_NO_HEARTBEAT',stage='paused',reason=str(exc),pid=None)
        except BaseException as exc:
            with self.mutation_lock:self.abort.set()
            self.state.update(status='STOPPED_ERROR',stage='halted',error=repr(exc),pid=None)
            raise
        finally:
            self.stop_pool();self.done.set();self.monitor.join(timeout=5)
            if self.state.get('root'):
                try:
                    folder=b.ROOT_OUT/self.state['root'];b.write_jsonl(folder/'partial_manifest.jsonl',list(merged_rows(folder).values()))
                except BaseException as exc:self.state['partial_manifest_error']=repr(exc)
            self.state['end_utc']=datetime.now(timezone.utc).isoformat();self.persist(force=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--workers',type=int,default=14);args=ap.parse_args()
    if not args.run:ap.error('--run required')
    import fcntl
    lock=(b.OUT/'bulk.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    old=b.read(b.OUT/'state.json')
    if old['status'] not in ('PAUSED_NO_HEARTBEAT','COMPLETE'):raise RuntimeError('Only explicitly safe checkpoints may resume')
    plan=b.read(b.OUT/'plan.json')
    for file,h in {**plan['protected_sources'],**plan['tool_sources']}.items():
        if b.sha(b.ROOT/file)!=h:raise RuntimeError('Source fingerprint changed: '+file)
    baseline=b.read(b.OUT/plan.get('active_inventory','parallel_inventory.json'));initial=sum(len(merged_rows(p)) for p in b.ROOT_OUT.iterdir() if p.is_dir())
    assert Path('/media/gpuadmin/One Touch').is_mount();b.heartbeat()
    if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
    runner=Runner(plan,baseline,initial,args.workers)
    def stop(*_):raise KeyboardInterrupt('Operator/system stop requested')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    runner.run()

if __name__=='__main__':main()
