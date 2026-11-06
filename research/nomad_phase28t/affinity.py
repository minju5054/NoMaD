"""Reserve one physical core for H; only this launcher's descendants are pinned."""
import os
from pathlib import Path

def choose(allowed,topology):
    allowed=sorted(allowed);groups={}
    for cpu in allowed:groups.setdefault(tuple(topology[cpu]),[]).append(cpu)
    if len(groups)<2:return dict(possible=False,allowed=allowed,driver_cpus=allowed,worker_cpu=None,reserved_siblings=[],reason='FEWER_THAN_TWO_PHYSICAL_CORES')
    key=max(groups);reserved=groups[key]
    return dict(possible=True,allowed=allowed,driver_cpus=[c for c in allowed if c not in reserved],worker_cpu=min(reserved),reserved_siblings=reserved,physical_core=list(key))

def plan():
    if not hasattr(os,'sched_getaffinity'):return dict(possible=False,reason='AFFINITY_API_UNAVAILABLE',worker_cpu=None,driver_cpus=[])
    allowed=sorted(os.sched_getaffinity(0));topology={}
    for cpu in allowed:
        root=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        try:topology[cpu]=(int((root/'physical_package_id').read_text()),int((root/'core_id').read_text()))
        except (OSError,ValueError):topology[cpu]=(0,cpu)
    return choose(allowed,topology)

def pin(cpus):
    try:
        before=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,set(cpus));after=sorted(os.sched_getaffinity(0))
        return dict(passed=set(after)==set(cpus),requested=sorted(cpus),before=before,actual=after,pid=os.getpid())
    except (OSError,AttributeError) as exc:return dict(passed=False,requested=sorted(cpus),reason=repr(exc),pid=os.getpid())
