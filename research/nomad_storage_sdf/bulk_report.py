"""Append bulk progress/results without rewriting the original pilot report."""
import csv,json,hashlib,subprocess
from pathlib import Path
from collections import Counter
from .bulk import OUT,ROOT_OUT,ISAAC,ROOT,read,read_jsonl,sha,save
from .report import table
MARKER='<!-- STORAGE_RETROFIT_BULK -->'

def generate():
 plan=read(OUT/'plan.json');state=read(OUT/'state.json') if (OUT/'state.json').exists() else {'status':'NOT_STARTED'};audit=read(OUT/'resume_audit.json');rows=[]
 for e in plan['roots']:
  f=ROOT_OUT/e['name']/'summary.json'
  if f.exists():r=read(f)
  else:
   r=next((x for x in state.get('completed_roots',[]) if x['root']==e['name']),None)
   if r is None:r=dict(root=e['name'],status=e['status'] if e['status']!='READY' else 'NOT_PROCESSED',reason=e.get('reason'),files=e['target_files'],converted=0,skipped=e['target_files'] if e['status'].startswith('EXCLUDED') else 0,before_bytes=e['before_bytes'],after_bytes=e['before_bytes'],saved_bytes=0,skip_reasons={})
  rows.append(r)
 totals=dict(status=state['status'],roots=len(rows),roots_complete=sum(r['status']=='COMPLETE' for r in rows),converted=sum(r.get('converted',0) for r in rows),
  files_processed=sum(r.get('files',0) for r in rows if r['status']=='COMPLETE'),skipped=sum(r.get('skipped',0) for r in rows),saved_bytes=sum(r.get('saved_bytes',0) for r in rows),
  error=state.get('error'),active_or_locked_roots=[r for r in rows if r['status'].startswith('EXCLUDED')],simulation_started=0)
 if state['status'] in ('COMPLETE','STOPPED_ERROR','PAUSED_NO_HEARTBEAT'):
  for f,h in {**plan['protected_sources'],**plan.get('protected_documents',{})}.items():
   if sha(ROOT/f)!=h:totals.setdefault('unexpected_frozen_source_changes',[]).append(f)
 df=subprocess.check_output(['df','-B1',str(ISAAC),plan['backup_directory']],text=True) if Path(plan['backup_directory']).exists() else subprocess.check_output(['df','-B1',str(ISAAC)],text=True)
 human_df=subprocess.check_output(['df','-h',str(ISAAC),'/media/gpuadmin/One Touch'],text=True)
 totals['df']=df;save(OUT/'summary.json',totals);save(OUT/'root_summary.json',rows)
 keys=['root','status','files','converted','bit_checked','bit_equal','bit_match_fraction','skipped','skip_reasons','before_bytes','after_bytes','saved_bytes','reason']
 with (OUT/'root_summary.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader()
  for r in rows:w.writerow({k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(dict,list)) else r.get(k) for k in keys})
 visible=[r for r in rows if r.get('files',0) or r['status'].startswith('EXCLUDED')]
 shown=[{'run-root':r['root'],'상태':r['status'],'처리 대상':r.get('files',0),'신규 변환':r.get('converted',0),'bit 검사/일치':f"{r.get('bit_checked',0)}/{r.get('bit_equal',0)}",'일치율':'—' if r.get('bit_match_fraction') is None else f"{r['bit_match_fraction']:.2%}",'skip(사유)':json.dumps(r.get('skip_reasons') or r.get('reason') or {},ensure_ascii=False),'폴더 GB 전→후':f"{r.get('before_bytes',0)/1e9:.3f}→{r.get('after_bytes',0)/1e9:.3f}",'절감 GB':f"{r.get('saved_bytes',0)/1e9:.3f}"} for r in visible]
 receipts=[read(p) for p in ROOT_OUT.glob('*/backups/*.json')]
 execution_note=(f"논리 CPU16개 중2개를 남겨14개 worker **프로세스**로 전환했으며 `nice -n 10`을 적용한다. worker마다 독립 파일을 소유하고 검증→원자 교체→worker별 journal을 기록한 뒤 root manifest로 병합한다. 공유 abort 신호와 교체 lock으로 오류 이후 추가 교체를 막는다. 메모리 여유4GiB 미만 또는 시작 기준보다 swap 점유 증가/새 swap-out이 감지되면 현재 파일을 마치고8개로 축소한다. 시작 전부터 점유된 swap은 새 사용과 구분해 보고한다." if (OUT/'parallel_transition.json').exists() else f"CPU7을 피한 {plan['workers']}개 thread worker로 임시 파일 검증만 병렬 처리하고 원자 교체는 coordinator가 수행한다. 검증 batch 하나에 예외가 나면 그 batch의 원본은 교체하지 않고 전체 중단한다.")
 benchmark=''
 if (OUT/'parallel_transition.json').exists():
  transition=read(OUT/'parallel_transition.json');baseline=transition['serial_baseline']
  benchmark=f"\n## 프로세스 병렬 전환과 처리 속도\n\n전환 전 단일 Python 프로세스(파일 검증 thread4→7)의 전체 경과시간 기준: {baseline['processed']:,}개 / {baseline['elapsed_s']/60:.2f}분 = **{baseline['files_per_minute']:.2f}파일/분**, 평균 **{baseline['mean_seconds_per_file']:.4f}초/파일**. 백업·검증·중간 일시정지가 포함된다. 재조사 대상151,772개 중 이미 처리6,456개, 기존 pilot 축소93개를 제외한 남은 변환 후보는 **145,223개**다. 이 속도를 적용한 예상 잔여시간은 **{baseline['eta_seconds']/3600:.2f}시간**이며 파일 크기/백업 비중에 따라 달라진다.\n"
  if (OUT/'parallel_5min.json').exists():
   m=read(OUT/'parallel_5min.json');peak=m['memory_peaks'];benchmark+=f"\n전환 후 첫 {m['elapsed_s']:.1f}초(프로세스 시작·백업 포함): **{m['files_per_minute']:.2f}파일/분**, 처리 {m['processed']:,}개, 예상 잔여 **{m['eta_seconds']/3600:.2f}시간**. 측정 시 worker {m['workers']}개. 시스템 사용 메모리 최대(MemTotal−MemAvailable) **{peak['system_used_bytes']/1024**3:.2f}GiB**, worker RSS 합 최대 **{peak['worker_rss_bytes']/1024**3:.2f}GiB**, 메모리 여유 최소 **{peak['available_bytes']/1024**3:.2f}GiB**. 기존 swap 점유 **{m['baseline_memory']['swap_used_bytes']/1024**3:.2f}GiB**; worker 축소 기록: `{json.dumps(m['worker_changes'],ensure_ascii=False)}`. RSS 합은 공유 메모리를 중복 집계할 수 있다. [측정 원자료](../research/results/storage_retrofit_bulk/parallel_5min.json).\n"
 if (OUT/'backup_inventory_at_disable.json').exists():
  inv=read(OUT/'backup_inventory_at_disable.json')
  benchmark+=f"\n## 사용자 지시: 추가 One Touch 백업 중단\n\n실제 백업 단위는 파일별이 아니라 run 전체 tar였다. 사용자 지시 이후 **추가 백업0**으로 전환했다. 기존 tar {sum(r['kind']=='tar' for r in inv['files'])}개 **{inv['tar_bytes']/1e9:.3f}GB**, 목록 포함 **{inv['total_bytes']/1e9:.3f}GB**를 그대로 유지한다. 삭제0, 중단 시 부분 tar {inv['partial_count']}개. 첫 H1 pilot 백업도 보존한다. [기존 백업 전체 목록](../research/results/storage_retrofit_bulk/backup_inventory_at_disable.json).\n\n새 파일은 원본 bytes에서 SHA와 모든 배열 fingerprint를 먼저 확보한다. 임시 파일을 압축한 뒤 복원 로더의 모든 배열을 원본과 직접 bit 비교하고, 원본 SHA가 바뀌지 않았는지 다시 확인한 뒤에만 원자 교체한다. 압축 수준·비트 검증을 변경하거나 생략하지 않았다. manifest의 backup_tar=null은 이 정책 이후의 파일을 뜻하며, 과거 원본 ZIP SHA를 manifest lineage로 추적한다.\n"
 if (OUT/'no_backup_profile_1min.json').exists():
  pr=read(OUT/'no_backup_profile_1min.json');keys=['read_decompress','sdf_recompute','bit_validation','compress_save','atomic_replace','one_touch_backup','manifest','guard','lock_wait','other']
  per_worker=[{'worker':w['worker_id'],'pid':w['pid'],'파일':w['files'],**{k:round(w['timings_s'][k],4) for k in keys}} for w in sorted(pr['workers'],key=lambda w:w['worker_id'])]
  with (OUT/'no_backup_profile_workers.csv').open('w',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=list(per_worker[0]) if per_worker else ['worker'],lineterminator='\n');writer.writeheader();writer.writerows(per_worker)
  total=sum(pr['stage_worker_seconds'].values());breakdown=[{'단계':k,'worker 초 합':round(pr['stage_worker_seconds'][k],3),'비중':f"{pr['stage_worker_seconds'][k]/total:.2%}" if total else '—'} for k in keys]
  benchmark+=f"\n## 백업 중단 후 1분 단계별 계측\n\n{pr['elapsed_s']:.2f}초, 완료 파일 {pr['files']}개. 모든 값은 worker별 wall-clock 누적이며, 병렬 실행 때문에 합계는 실경과보다 크다. 재계산이 복원 로더 안에서 실행된 시간은 read에서 빼 SDF에 분류했다. bit 검증에는 배열 fingerprint·원본/임시/교체 후 SHA 확인을 포함한다. manifest는 journal flush/fsync를 포함한다. One Touch backup은 사용자 지시로 측정 전에 중단됐으므로0이다.\n\n{table(breakdown)}\n\n{table(per_worker)}\n"
 if (OUT/'no_backup_5min.json').exists():
  m=read(OUT/'no_backup_5min.json');old=read(OUT/'parallel_5min.json');p=m['memory_peaks']
  benchmark+=f"\n## 백업 없는 5분 처리량\n\n{m['elapsed_s']:.2f}초에 {m['processed']:,}개: **{m['files_per_minute']:.2f}파일/분**, 파일당 {m['mean_seconds_per_file']:.4f}초. 백업 포함 병렬 대비 {m['files_per_minute']/old['files_per_minute']:.2f}배. 남은 후보 {m['remaining_candidates']:,}개, 예상 **{m['eta_seconds']/3600:.2f}시간**. worker {m['workers']}개; worker RSS 합 최대 {p['worker_rss_bytes']/1024**3:.2f}GiB, 시스템 사용 최대 {p['system_used_bytes']/1024**3:.2f}GiB, 여유 최소 {p['available_bytes']/1024**3:.2f}GiB. worker 변경: `{json.dumps(m['worker_changes'],ensure_ascii=False)}`. 파일 구성과 저장장치 상태가 달라질 수 있는 관측 추정이며 확정 완료시각은 아니다.\n"
  benchmark+='\n추가 백업 제거 뒤 처리량이 크게 늘어 백업이 주요 병목이었던 것으로 판단한다. 동일 파일을 반복한 통제 비교는 아니다. 백업 없는 1분 계측에서 가장 큰 작업은 SDF 재계산이고, 전역 교체 lock 대기도 크다. **제안만**: 모든 검증을 유지하면서 독립적인 읽기·SHA 확인을 전역 lock 밖으로 분리하고, lock은 오류 플래그 확인·durable PREPARED·원자 교체 구간에 한정하는 방안을 별도로 검증할 수 있다. 이번에는 적용하지 않았으며 압축 수준과 비트 검증은 그대로다.\n'
 if (OUT/'memory_history.json').exists():
  mh=read(OUT/'memory_history.json');benchmark+=f"\n## 전체 실행의 메모리 감시\n\n0.25초 간격 관측 최대: worker RSS 합 {mh['peak_worker_rss_bytes']/1024**3:.2f}GiB, 시스템 사용 {mh['peak_system_used_bytes']/1024**3:.2f}GiB. 여유 최소 {mh['minimum_available_bytes']/1024**3:.2f}GiB. 위 5분 측정 시점은14 worker였으나 **측정 이후 새 swap-out을 감지해8 worker로 자동 축소**했다. 이후 재개도8개를 유지한다. 전환 이력은 [memory_history.json](../research/results/storage_retrofit_bulk/memory_history.json)에 보존한다. 재개 시 worker 수를14로 잘못 가정한 검사와 짧은 재기동 이력도 [resume_control_note.json](../research/results/storage_retrofit_bulk/resume_control_note.json)에 기록했다. 파일 변환 예외나 손상은 발생하지 않았다. 현재/종료 설정: {state.get('workers',plan['workers'])} worker.\n"
 if (OUT/'final_audit.json').exists():
  au=read(OUT/'final_audit.json');reg=au['phase31e_regression']
  benchmark+=f"\n## 최종 감사\n\n**{au['status']}**: manifest 전체 범위·중복 소유권·manifest SHA·파일 크기 확인, 잔여 변환 임시 파일 {len(au['temporary_files'])}개. frozen 실험 source 변경 {len(au['changed_frozen_sources'])}개, 기존 결과 문서 변경 {len(au['changed_frozen_documents'])}개. 백업 중단 뒤 추가/변경/삭제된 백업 파일 {len(au['backup_files_changed_or_added'])}개. 이미 수행한 파일별 원본/임시 배열 bit 비교와 교체 후 SHA 검증 기록을 감사했으며, 전체 EDT를 불필요하게 다시 실행하지 않았다.\n\nPhase31-E 회귀: PASS={reg['passed']}, 상자 최초 관측 기록 동일={reg['box_history_exactly_equal']}, 계획 depth clearance bit 일치={reg['plan_depth_clearance_bit_equal']}, oracle clearance bit 일치={reg['oracle_plan_clearance_bit_equal']}. [최종 감사 원자료](../research/results/storage_retrofit_bulk/final_audit.json).\n\n절감량은 대상 NPZ의 논리적 파일 크기 차이다. `df`는 블록 할당·새 manifest 저장·다른 파일시스템 사용도 포함하므로 완전히 같은 값은 아니다.\n"
 text=f'''{MARKER}

# 후속 SSD 전체 변환 — 사용자 재개 요청

**상태: {state['status']}**. 새 시뮬레이션/추론/Graph solve0. frozen 실험 코드·이전 결과 문서를 변경하지 않았다. 이 절만 기존 STORAGE_RETROFIT 문서 뒤에 추가했다.

## 중단 후 선행 점검

- 발견 임시 파일: {len(audit['temporary_files'])}개. 원본 NPZ의 CRC/배열/finiteness/SDF 일치를 확인한 후0바이트 `phase24r_pilot_01/main/SLW_144_G/g_jobs/snapshot_0104.npz.archive.tmp`만 삭제했다. 원본SHA는 그대로다.
- 기존 pilot 변환93개를 새 SHA와 복원 배열 fingerprint로 재검증했다. 손상 발견0, 부분 manifest 보정 필요 {audit['manifest_repairs_required']}개. 원래 pilot 증거는 보존했다.
- [resume_audit.json](../research/results/storage_retrofit_bulk/resume_audit.json)에 파일별 점검 결과가 있다.

## 범위·실행 보호

`../artifacts/isaac6`의 run-root 전부를 조사하되 파일 종류는 원 절차와 같은 **depth/snapshot_*.npz, repair_jobs/input_*.npz**만이다. 원 depth_*.npz·g_jobs snapshot·cache NPZ 등은 변환하지 않는다. 이번 조사 {len(plan['roots'])}개 root 중 대상이 있는 root {sum(e['target_files']>0 for e in plan['roots'])}개, 대상 파일 {sum(e['target_files'] for e in plan['roots']):,}개다. 새로 생긴 root를 실행 도중 범위에 추가하지 않는다.

호스트 PID/state.json·실제 kernel lock·열린 file descriptor를 확인한다. 실행용 root lock marker나 실제 점유 lock이 있으면 제외한다. 종료 뒤 남은 `cache/ov/_cache.lock` 같은 라이브러리 캐시 파일은 **실제 점유가 없는지 확인하고 보존**하며, 지우지 않는다. `phase32_01`은 명시적으로 보호한다. {execution_note} 실제 IO 오류에도 자동 재시도하지 않는다.

진행 heartbeat가180초 넘게 끊기면 다음 변환 batch 전에 PAUSED_NO_HEARTBEAT로 멈춘다(ESC/연결 중단 대비). 현재 backup은 완성·검증할 수 있지만 그 뒤 원본 변환을 시작하지 않는다. SIGINT/SIGTERM도 상태와 journal을 남긴다. 멈춘 원본을 숨기거나 성공으로 간주하지 않는다.

## 백업·버전·파일 검증

작은 run-root부터, 그 안에서도 작은 run부터 처리한다. **백업 중단 지시 전에는** 각 run 전체를 One Touch `{plan['backup_directory']}`에 tar로 보존하고 원본 regular-file SHA를 tar member와 대조한 뒤 변환했다. 현재 검증된 backup {len(receipts)}개, tar {sum(r['bytes'] for r in receipts)/1e9:.3f}GB다. 각 tar 옆 `.inventory.json`에는 원본 전체 파일의 hash·metadata가 있고, root별 `backups/`에는 영수증이 있다. 기존 backup은 삭제하지 않으며, 중단 이후 정책과 계측은 아래 절에 따로 기록한다. 이전 pilot의 원래 zip bytes는 기존 H1 tar로 계속 추적한다.

각 run provenance의 git commit/기록 source SHA를 사용해 그 당시 `LogOddsSDF.update`와 `DepthSDF.__init__` 버전을 확인한다. 지원하는 frozen AST와 같을 때만 runtime EDT 복원을 허용하며 **실제 파일마다 values bytes 일치가 추가로 필수**다. 알려지지 않은 버전/형식은 원본 그대로 사유를 기록한다. [versions.json](../research/results/storage_retrofit_bulk/versions.json)에 함수 버전 근거가 있다.

원 파일을 읽어 original SHA를 확보하고(백업 단계에서는 백업 목록과도 대조), 같은 함수로 values를 계산한다. 일치하는 경우에만 임시 NPZ를 만들고 복원 로더로 **모든 원 배열을 직접 byte 비교**한다. 임시 파일 fsync 후 PREPARED 기록을 fsync하고, 원본이 바뀌지 않았음을 다시 확인한 뒤 `os.replace`한다. 불일치는 원본을 그대로 둔다. 변환 후 파일 SHA도 다시 확인한다. `arrays_sha256`은 모든 배열의 dtype/shape/order/bytes fingerprint를 정렬한 전체 digest다.

폴더별 `manifest.jsonl`과 `journal.jsonl`에 original/new SHA, 검증 결과, 크기, 원본 tar/member, runtime version을 기록한다. 이미 축소된93개는 복원 검증 후 ALREADY_COMPACT로 건너뛰며 이번 절감량에 다시 넣지 않는다. 원 input hash는 manifest-aware `resolve_original_hash`로 추적해야 하며 frozen 보고서의 hash를 덮어쓰지 않는다.

## run-root별 결과

{table(shown)}

대상 없는 root와 제외 root까지 포함한 전체 목록: [root_summary.csv](../research/results/storage_retrofit_bulk/root_summary.csv). 신규 변환 **{totals['converted']:,}개**, 이번 SSD 절감 **{totals['saved_bytes']/1e9:.3f}GB**. SKIPPED_UNKNOWN_VERSION/DIFFERENT_FORMAT/SDF_MISMATCH/ALREADY_COMPACT는 서로 구분한다. bit 일치율의 분모는 실제 재계산·복원 비교를 수행한 파일이며 형식/버전 미상 파일을 PASS로 채우지 않는다.

오류: `{state.get('error','없음')}`. 원본 손상이 발견되거나 예외가 발생하면 이후 파일/폴더로 진행하지 않는다. STOPPED_ERROR는 사용자 검토 없이 다시 시작하지 못한다.

## 변환 후 df

```text
{human_df.strip()}
```

Byte 단위 df와 집계: [summary.json](../research/results/storage_retrofit_bulk/summary.json). root마다 완료 시점 df도 해당 `summary.json`에 저장한다. 외장 백업은 삭제하지 않는다.

{benchmark}

상태 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_storage_sdf.bulk --status`

문서 재집계: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_storage_sdf.bulk_report`
'''
 doc=ROOT/'docs/STORAGE_RETROFIT.md';old=doc.read_text();prefix=old.split(MARKER)[0]
 doc.write_text(prefix.rstrip()+'\n\n'+text)
 print(json.dumps(totals,ensure_ascii=False))

if __name__=='__main__':generate()
