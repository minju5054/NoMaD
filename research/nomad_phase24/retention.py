"""Archive-only adapters. All RGB/depth capture, map updates and inputs stay live."""
import ast,functools,inspect,json,os,time,hashlib
from pathlib import Path

def full_frames():return os.environ.get('NOMAD_PHASE24_FULL_FRAMES','1')=='1'

class GuardRGBWrites(ast.NodeTransformer):
    def __init__(self):self.count=0
    def visit_Expr(self,node):
        call=node.value
        if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='save' and ast.unparse(call.func.value).startswith('Image.fromarray('):
            self.count+=1
            return ast.If(test=ast.Name(id='_phase24_full_frames',ctx=ast.Load()),body=[node],orelse=[])
        return self.generic_visit(node)

def run_without_oracle(*args,**kwargs):
    from nomad_phase20f.runtime import run_without_oracle as original
    if full_frames():return original(*args,**kwargs)
    import nomad_isaac.async_runtime as runtime
    tree=ast.parse(inspect.getsource(runtime.run_async));fn=tree.body[0];changed=0
    for i,node in enumerate(fn.body):
        if isinstance(node,ast.If) and ast.unparse(node.test)=='s1 and engine.dynamic is not None':
            fn.body[i]=ast.Assign(targets=[ast.Name(id='oracle_gate',ctx=ast.Store())],value=ast.Constant(value=None));changed+=1
    assert changed==1  # Exact same oracle-publication removal as frozen20F.
    guard=GuardRGBWrites();tree=guard.visit(tree);assert guard.count==4
    namespace=dict(runtime.__dict__,_phase24_full_frames=False)
    exec(compile(ast.fix_missing_locations(tree),runtime.__file__,'exec'),namespace)
    return namespace['run_async'](*args,**kwargs)

def retained_apply(execution):
    """Retain the map(s) read around a FRESH, without changing the method call."""
    original=execution.apply
    @functools.wraps(original)
    def apply(core,refresh,switch):
        maps=execution.depth_maps
        if switch is not None and hasattr(maps,'retain_latest'):maps.retain_latest()
        try:return original(core,refresh,switch)
        finally:
            if switch is not None and hasattr(maps,'retain_latest'):maps.retain_latest()
    execution.apply=apply;return execution

def archive_compact(owner):
    """Separate archival queue; the original publisher and immutable SDF stay intact."""
    buckets=set();written=set()
    try:
        while True:
            item=owner.archive_queue.get()
            if item is None:break
            snap,depth,transform=item;start=time.monotonic_ns();frame=snap.metadata['frame_id'];bucket=int(snap.metadata['sim_s']);forced=depth is None
            keep=forced or bucket not in buckets
            if not forced:buckets.add(bucket)
            path=Path(snap.metadata['file']);digest=None
            if keep and frame not in written:
                snap.save(path);written.add(frame);digest=hashlib.sha256(path.read_bytes()).hexdigest()
            owner.alog.write(json.dumps(dict(frame_id=frame,file=str(path),archive_start_ns=start,archive_end_ns=time.monotonic_ns(),
                retained=frame in written,reason='FRESH' if forced else 'VISUALIZATION_1HZ' if keep else 'OMITTED_UNUSED_MAP',snapshot_sha256=digest,raw_depth_stored=False))+'\n');owner.alog.flush()
    except BaseException as exc:owner.error=exc

def install_depth_retention():
    # Called only after SimulationApp; never pull scipy into the launcher.
    from nomad_phase20f.depth import DepthMapThread as Original
    import nomad_phase15b.depth as target
    class ArchiveOnlyDepth(Original):
        def __init__(self,*args,**kwargs):self.full_frames=full_frames();super().__init__(*args,**kwargs)
        def archive(self):
            if self.full_frames:return super().archive()
            return archive_compact(self)
        def retain_latest(self):
            if not self.full_frames:self.archive_queue.put_nowait((self.snapshot(),None,None))
    target.DepthMapThread=ArchiveOnlyDepth
