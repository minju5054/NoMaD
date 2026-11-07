import argparse,json,csv,subprocess
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_phase26.metrics import audit as original_audit
from nomad_phase29.metrics import audit as graph_audit
from nomad_phase31p.report import table,csv_write,save,median
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify

def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x] if Path(p).exists() else []
def baselines():return json.loads((OUT/'preparation/baselines.json').read_text())

def fallback_counts(events):
 counts=Counter()
 for e in events:
  if e['event']=='INSTALL' and e['route'] in ('NEXT_SAFE_FULL','SAFE_SLOW'):counts[e['route']]+=1
  elif e['event']=='FALLBACK':counts[e['route']]+=1
  elif e['event']=='SOLVER_FILTER' and e['route'] in ('R2_TO_R3','R3_FAILURE'):counts[e['route']]+=1
  elif e['event']=='PERIODIC_APPLY' and e['action'] in ('R2_TO_R3','R3_FAILURE'):counts[e['action']]+=1
 return dict(counts)

def audit(root):
 root=Path(root);cfg=json.loads((root/'scenario.json').read_text());r=graph_audit(root) if cfg['phase32_method']=='G18+EC' else original_audit(root)
 ev=lines(root/'exec_cert.jsonl');ticks=lines(root/'exec_cert_72hz.jsonl');checks=[x for x in ev if x['event']=='CHECK'];installs=[x for x in ev if x['event']=='INSTALL'];periodic=[x for x in ev if x['event']=='PERIODIC_APPLY'];elapsed=r['duration_s']
 assert ticks and max(x['tick'] for x in ticks)==round(elapsed*72)
 r.update(method=cfg['phase32_method'],mean_speed_m_s=r['distance_m']/elapsed,ec_checks=len(checks),ec_rejects=sum(not x['passed'] for x in checks),
  ec_by_state={s:dict(checks=sum(x['state']==s for x in checks),rejects=sum(x['state']==s and not x['passed'] for x in checks)) for s in ('NORMAL','R2','R3')},
  ec_compute_p50_s=median([x['compute_s'] for x in checks]),ec_compute_p95_s=float(np.quantile([x['compute_s'] for x in checks],.95)) if checks else None,
  ec_fallback_routes=fallback_counts(ev),ec_all_routes=dict(Counter(x['route'] for x in ev if x['event'] in ('INSTALL','FALLBACK','SOLVER_FILTER'))),
  ec_slow_installs=sum(x['speed_cap_m_s'] is not None for x in installs),ec_slow_activations=sum(x.get('cap_activated',False) for x in installs),ec_slow_ranks=[x['freshest_rank'] for x in installs if x['speed_cap_m_s'] is not None and x['freshest_rank'] is not None],
  ec_slow_held_s=sum(x['speed_cap_active'] for x in ticks)/72,
  ec_reject_stopped_s=sum(x['ec_reject_latched'] and x['physical_stop'] for x in ticks)/72,
  ec_reject_stop_wait_s=sum(x['ec_reject_latched'] and x['physical_stop'] and x['mode']=='STOP_WAIT' and x['recovery_state']=='NORMAL' for x in ticks)/72,
  ec_periodic_delays_ticks=[x['delay_ticks'] for x in periodic],ec_periodic_delays_wall_ms=[x['delay_wall_ms'] for x in periodic],ec_periodic_max_delay_ms=max([x['delay_ms'] for x in periodic],default=None))
 assert all(0<=x<=4 for x in r['ec_periodic_delays_ticks']);return r

def decide(rows,old):
 keys={(s,i,m) for s in SCENES for i in INDICES for m in METHODS};have=[(r['scene'],r['index'],r['method']) for r in rows]
 valid=len(rows)==30 and set(have)==keys and all(r['technical_validation']=='PASS' and r.get('collision') is not None for r in rows)
 n_goal=sum(bool(r.get('success')) for r in rows);n_coll=sum(bool(r.get('collision')) for r in rows);b_goal=sum(r['success'] for r in old);b_coll=sum(r['collision'] for r in old)
 checks=dict(collision_strictly_less=n_coll<b_coll,goal_at_least_baseline_minus_one=n_goal>=b_goal-1)
 return dict(label='EC_HELPS' if valid and all(checks.values()) else 'EC_NO_HELP',evidence_valid=valid,checks=checks,ec_goal=n_goal,ec_collision=n_coll,baseline_goal=b_goal,baseline_collision=b_coll,
  reason='registered predicates' if valid else 'incomplete/technically invalid30-run evidence; no improvement claim',historical_execution_days_differ=True)

def summary(rows,group):
 result=[]
 for m in sorted({r['method'] for r in rows}):
  for scene in (*SCENES,'ALL'):
   rs=[r for r in rows if r['method']==m and (scene=='ALL' or r['scene']==scene)];valid=[r for r in rs if r['technical_validation']=='PASS']
   if not rs:continue
   checks=sum(r.get('ec_checks',0) for r in valid);rejects=sum(r.get('ec_rejects',0) for r in valid)
   result.append(dict(group=group,method=m,scene=scene,n=len(rs),valid=len(valid),goal=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),
    goal_time_median_s=median([r['goal_time_s'] for r in valid if r['success']]),stop_fraction_median=median([r['stopped_fraction'] for r in valid]),ec_checks=checks,ec_rejects=rejects,ec_reject_rate=rejects/checks if checks else None,
    ec_reject_stopped_s=sum(r.get('ec_reject_stopped_s',0) for r in valid),slow_held_s=sum(r.get('ec_slow_held_s',0) for r in valid)))
 return result

def generate(root):
 p=verify();rows=[json.loads(x.read_text()) for x in sorted((root/'metrics').glob('*.json'))];old=baselines();d=decide(rows,old);stats=summary(rows,'Phase32 EC')+summary(old,'historical different-day')
 pairs=[]
 for r in rows:
  b=next(x for x in old if (x['scene'],x['index'],x['method'])==(r['scene'],r['index'],r['method'].removesuffix('+EC')))
  pairs.append(dict(scene=r['scene'],index=r['index'],method=r['method'],ec_goal=r.get('success'),baseline_goal=b['success'],ec_collision=r.get('collision'),baseline_collision=b['collision'],goal_time_delta_s=r['goal_time_s']-b['goal_time_s'] if r.get('success') and b['success'] else None,baseline_output=b['output']))
 OUT.mkdir(parents=True,exist_ok=True);save(OUT/'runs.json',rows);save(OUT/'decision.json',d);csv_write(OUT/'summary.csv',stats);csv_write(OUT/'paired.csv',pairs)
 details=[dict(method=r['method'],scene=r['scene'],index=r['index'],**{k:v for k,v in r.items() if k.startswith('ec_')}) for r in rows];save(OUT/'ec_metrics.json',details)
 timing=[]
 for method in METHODS:
  values=[x['compute_s'] for r in rows if r['method']==method and r['technical_validation']=='PASS' for x in lines(Path(r['output'])/'exec_cert.jsonl') if x['event']=='CHECK']
  timing.append(dict(method=method,n=len(values),p50_s=median(values),p95_s=float(np.quantile(values,.95)) if values else None))
 save(OUT/'ec_timing.json',timing)
 sha=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest()
 doc=ROOT/'docs/PHASE32_RESULTS.md';doc.write_text('# Phase32 EC 실행 비교\n\n**'+d['label']+'**. Protocol SHA256 `'+sha+'`.\n\n'+table([d])+'\n\n## 사용자 승인 사전등록 이탈\n\n2026-11-07: Phase32-O OFFLINE_FAIL(전체 위치오차 p95 0.030037125m >0.03m)을 그대로 보존한다. 동일 C0-NA 구간 오차0m라는 근거로 사용자 승인에 따라 온라인 비교를 준비/실행했다. 오프라인 판정을 PASS로 바꾸지 않았다.\n\n## 방법×장면\n\n'+table(stats)+'\n\n'+table(pairs)+'\n\n기존 C0-NA/G18은 같은 scene×seed지만 다른 날 실행된 역사적 비교다. C0-NA201/202는Phase28,203~205는Phase29 confirm; G18은Phase29 dev/confirm이다. Phase31-P는206/207이라 이번 비교 키에 없다.\n\n## EC 메커니즘\n\n'+table(details)+'\n\n'+table(timing)+'\n\nCHECK는 candidate별 검사 호출 수(따라서 R3 한 job에 여러 검사)다. INSTALL/주기 검사와 상태를 로그에 분리했다. 감속 유지시간은cap latch 활성 시간(정지 포함), REJECT 정지시간은rejection latch 후 실제|v|<0.01인시간이며 STOP_WAIT/회복/계산대기를 로그로 분리할 수 있다. 주기검사는36tick, 적용은 다음9Hz tick이며0/4tick(최대55.56ms) simulation-clock 지연과 별도의 실제 wall-clock 지연을 모두 남긴다.\n')
 return doc

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
 if a.publish:
  paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
  if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase32 execution certificate pilot','--',*paths],cwd=ROOT,check=True)
  subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
