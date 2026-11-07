"""Report a finished one-run storage pilot. No conversion/bulk action here."""
import csv,json,hashlib,shutil
from pathlib import Path
from collections import Counter,defaultdict
from .pilot import ROOT,PILOT,OUT,BACKUP_DIR,read,save,sha


def table(rows):
 if not rows:return '없음'
 keys=list(rows[0]);return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(str(r[k]) for k in keys)+' |' for r in rows])
def csvout(path,rows):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
 dry=read(OUT/'dry_run.json');manifest=read(OUT/'manifest.json');v=read(OUT/'verification.json');backup=read(OUT/'backup.json');before=read(OUT/'phase31e_before.json');after=read(OUT/'phase31e_after.json');est=read(OUT/'ssd_estimates.json');inventory=read(OUT/'ssd_inventory.json');raw=read(OUT/'ssd_raw_depth_inventory.json');samples=read(OUT/'ssd_compression_samples.json');refs=read(OUT/'report_hash_lineage.json')
 assert before==after and v['phase31e_equal'] and v['restored_files_bit_equal']==len(manifest)
 assert all(r['literal_backup_array_bits_equal'] for r in manifest)
 for f,h in dry['runtime_sources'].items():assert sha(ROOT/f)==h,f
 categories=[]
 for key,label in [('depth_raw','depth/depth_*.npz(원 depth)'),('snapshots','depth/snapshot_*.npz'),('repair_inputs','repair_jobs/input_*.npz')]:
  a=dry['categories_before'][key];b=v['categories_after'][key];categories.append({'종류':label,'파일 수':a['count'],'이전 bytes':a['bytes'],'이후 bytes':b['bytes'],'이전 MB':f"{a['bytes']/1e6:.6f}",'이후 MB':f"{b['bytes']/1e6:.6f}",'절감 MB':f"{(a['bytes']-b['bytes'])/1e6:.6f}"})
 total_before=sum(r['original_bytes'] for r in manifest);total_after=sum(r['new_bytes'] for r in manifest);saved=total_before-total_after;allocated_saved=sum(r['original_allocated_bytes']-r['new_allocated_bytes'] for r in manifest)
 original_inv=read(OUT/'run_inventory_before.json');run_before=sum(r['size'] for r in original_inv if r['kind']=='file');run_after=run_before-saved
 whole=[]
 for root in sorted({r['root'] for r in inventory}):
  ss=[r for r in inventory if r['root']==root and r['kind']=='snapshot'];ii=[r for r in inventory if r['root']==root and r['kind']=='repair_input'];dd=[r for r in raw if r['root']==root];ee=[r for r in est if r['root']==root]
  whole.append(dict(root=root,snapshot_count=len(ss),snapshot_bytes=sum(r['bytes'] for r in ss),repair_input_count=len(ii),repair_input_bytes=sum(r['bytes'] for r in ii),depth_raw_count=len(dd),depth_raw_bytes=sum(r['bytes'] for r in dd),
   estimated_saved_bytes=sum(r['estimated_saved_bytes'] for r in ee),estimated_after_bytes=sum(r['estimated_after_bytes'] for r in ee),sensitivity_low_bytes=sum(r['saved_sensitivity_low_bytes'] for r in ee),sensitivity_high_bytes=sum(r['saved_sensitivity_high_bytes'] for r in ee)))
 csvout(OUT/'ssd_summary.csv',whole)
 csvout(OUT/'conversion_manifest.csv',[{k:r[k] for k in ('path','status','original_sha256','new_sha256','values_bit_equal','other_arrays_bit_equal','literal_backup_array_bits_equal','original_bytes','new_bytes','backup_tar','backup_member')} for r in manifest])
 predicted=sum(r['estimated_saved_bytes'] for r in est);low=sum(r['saved_sensitivity_low_bytes'] for r in est);high=sum(r['saved_sensitivity_high_bytes'] for r in est)
 summary=dict(pilot=str(PILOT),snapshot_count=dry['categories_before']['snapshots']['count'],repair_input_count=dry['categories_before']['repair_inputs']['count'],total_target_files=len(manifest),values_bit_equal_files=dry['bit_equal'],bit_equal_fraction=dry['bit_equal']/len(manifest),
  converted=sum(r['status']=='CONVERTED' for r in manifest),skipped=sum(r['status']!='CONVERTED' for r in manifest),target_before_bytes=total_before,target_after_bytes=total_after,saved_ssd_bytes=saved,saved_allocated_bytes=allocated_saved,
  run_regular_files_before_bytes=run_before,run_regular_files_after_bytes=run_after,backup=backup,arrays_literal_verified=v['literal_backup_arrays_compared'],phase31e_equal=True,old_report_hash_links=len(refs),
  wide_inventory_target_files=len(inventory),wide_target_before_bytes=sum(r['bytes'] for r in inventory),wide_raw_depth_files=len(raw),wide_raw_depth_bytes=sum(r['bytes'] for r in raw),
  wide_compression_samples=len(samples),wide_sample_bit_matches=sum(r['bit_equal'] for r in samples),wide_estimated_saved_bytes=predicted,wide_saved_sensitivity_bytes=[low,high],wide_other_runs_modified=False,
  ssd_free_bytes_after=shutil.disk_usage(ROOT).free,units='MB/GB decimal, GiB binary when explicitly indicated',tests_passed=6,
  tool_sha256={str(f.relative_to(ROOT)):sha(f) for f in Path(__file__).parent.glob('*.py')})
 save(OUT/'summary.json',summary)
 whole_table=[{'범위':r['root'],'snapshot 수':r['snapshot_count'],'snapshot GB':f"{r['snapshot_bytes']/1e9:.3f}",'input 수':r['repair_input_count'],'input GB':f"{r['repair_input_bytes']/1e9:.3f}",'원 depth 수':r['depth_raw_count'],'원 depth GB':f"{r['depth_raw_bytes']/1e9:.3f}",'예상 절감 GB':f"{r['estimated_saved_bytes']/1e9:.3f}"} for r in whole]
 agreement=[{'Phase31-E 지표':'상자 최초 occupied capture(s)','변환 전':before['box_history']['box_first_occupied_capture_s'],'변환 후':after['box_history']['box_first_occupied_capture_s'],'검증':'정확 일치'},
  {'Phase31-E 지표':'최초 snapshot 발행(s)','변환 전':before['box_history']['box_first_occupied_publish_s'],'변환 후':after['box_history']['box_first_occupied_publish_s'],'검증':'정확 일치'},
  {'Phase31-E 지표':'계획 base-depth exact 여유(m)','변환 전':before['planning_base_exact_clearance_m'],'변환 후':after['planning_base_exact_clearance_m'],'검증':'float64 bytes 일치'},
  {'Phase31-E 지표':'계획 oracle 여유(m, 평가만)','변환 전':before['oracle_plan_suffix_m'],'변환 후':after['oracle_plan_suffix_m'],'검증':'float64 bytes 일치'}]
 text=f'''# Storage retrofit — 한 run SDF values 제거·복원 검증

**완료 범위: `phase29_01/dev/H1_201_G18/attempt1` 한 run만.** 새 시뮬레이션·추론·Graph 풀이·패키지 설치0. frozen 실험 코드·기존 결과 문서는 변경하지 않았다. 다른 run은 읽기 전용 용량 추정만 했다.

- snapshot **{dry['categories_before']['snapshots']['count']}개** + repair input **{dry['categories_before']['repair_inputs']['count']}개** = **{len(manifest)}개**, values 재계산 비트 일치 **{dry['bit_equal']}/{len(manifest)} (100%)**. 모두 변환, 건너뜀0.
- 대상 NPZ **{total_before/1e6:.6f}MB → {total_after/1e6:.6f}MB**, SSD 논리 크기 **{saved/1e6:.6f}MB ({saved/total_before:.2%}) 절감**. 할당 block 기준 절감 {allocated_saved/1e6:.6f}MB.
- 복원한 **{v['literal_backup_arrays_compared']}개 배열**을 tar 원본 배열과 직접 byte 비교해 모두 일치했다(values 포함, dtype/shape/Fortran order 보존).
- Phase31-E 최초 상자 관측 및 계획 여유 계산 동일. 기존 input hash 참조 **{len(refs)}개**가 old SHA→new SHA→원본 tar member로 검증됐다.
- SSD 지정 범위 전체에 같은 방식을 적용하면 **약 {predicted/1e9:.1f}GB 절감 예상**. 이는 표본 기반 추정이며 bulk 변환은 실행하지 않았다.

## 1. 백업 → dry-run/변환 → 복원 검증

실제 순서는 읽기 전용 dry-run → 원본 run 전체 tar 백업 및검증 → 해당93개만 atomic 교체 → 복원/기존 분석 검산이다. 백업은 **변환 전에** 완료했다.

백업 파일:

`{backup['archive']}`

- tar 크기: **{backup['archive_bytes']:,}bytes ({backup['archive_bytes']/1e9:.6f}GB)**.
- SHA256: `{backup['archive_sha256']}`.
- run의 정규 파일 **{backup['verified_regular_files']}개 전부** tar member SHA256이 원본과 같음을 확인했다. 디렉터리 포함 검증 member {backup['verified_members']}개.
- 같은 One Touch 폴더의 `.tar.inventory.json`은 원본 파일별 SHA256/크기/mtime/mode 목록이다. SSD 쪽 [backup.json](../research/results/storage_retrofit/backup.json)과 [run_inventory_before.json](../research/results/storage_retrofit/run_inventory_before.json)에도 영수증과 목록을 보존했다.
- 원본 run의 정규 파일 총합은 {run_before/1e9:.6f}GB → {run_after/1e9:.6f}GB다. tar 백업은 SSD가 아닌 One Touch 공간을 사용한다. 전체 저장장치 사용량이 그만큼 줄었다는 뜻은 아니다.

단위테스트6개 통과: bit-exact round trip(NaN payload/negative zero/Fortran 배열 포함),1ULP values 차이 시 원파일 미변경, 기존 Snapshot.load의 opt-in 복원, empty grid, hash 변조 거부, dry-run 이후 원본 변경 시 변환 거부.

## 2. 정확히 무엇을 바꿨는가

대상 패턴은 **`depth/snapshot_*.npz`와 `repair_jobs/input_*.npz`만**이다(`snapshot_initial.npz` 포함). `depth/depth_*.npz`, `depth/final.npz`, cache NPZ, RGB, CSV, JSON/JSONL 로그와 그 외 run 파일은 원본 SHA256이 유지됐다. 변환 대상으로 지정한93개 이외 정규 파일 {backup['verified_regular_files']-len(manifest)}개가 그대로다.

{table(categories)}

values는 현재 런타임의 `nomad_phase15.occupancy.distance_transform_edt`를 그대로 호출해 `distance_transform_edt(~occupied, sampling=h) - radius`로 계산한다. 별도 EDT·근사·float16 변환·양자화가 없다. empty grid는 origin/h/shape로 범위를 복원해 원 `DepthSDF`의 empty-distance 계산을 사용한다. 저장되지 않은 실제 bound의 부동소수 반올림 때문에 일치하지 않는 파일은 **values를 포함한 원 NPZ 전체를 그대로 둔다**. 이번93개는 empty grid까지 모두 일치했다.

매 파일에서 dtype·shape·배열의 모든 bit가 같은 경우에만 values를 제외하고 `np.savez_compressed`로 다시 쓴다. 나머지 배열의 dtype/order/내용을 보존하고, 같은 디렉터리 임시 파일을 fsync·복원 검증한 후 atomic replace한다. `original_sha256/new_sha256`의 PREPARED 기록을 교체 전에 fsync하여 중단되어도 대응을 추적할 수 있다. mismatch 파일은 압축만 다시 하는 것도 하지 않는다. 파일 mode/mtime도 유지했다.

현재 검증 환경: Python {dry['python']}, NumPy {dry['numpy']}, SciPy {dry['scipy']}, zlib {dry['zlib']}. 원 런타임 함수 소스 hash는 [dry_run.json](../research/results/storage_retrofit/dry_run.json)에 고정했다. 다른 환경으로 옮겨 재계산할 때도 manifest의 배열 fingerprint 검증을 통과해야 한다.

## 3. 복원 로더와 frozen 분석 검증

새 도구는 `research/nomad_storage_sdf/`에만 추가했다.

```python
from nomad_storage_sdf.loader import load_npz
arrays = load_npz(path)  # 일반/축소 NPZ 모두 원래 key/array의 dict
```

`values`가 있으면 그대로 읽는다. 없으면 occupied/origin/h/radius에서 재계산해 반환한다. `load_npz(path, manifest_row['original_arrays'])`를 쓰면 복원 결과의 모든 배열 fingerprint도 검증한다. 복원에는 One Touch가 필요 없지만 원래 **NPZ 파일 bytes 자체**가 필요하면 tar에서 해당 member를 읽어야 한다. 재압축 후 NPZ 파일 SHA256은 원래와 같지 않다.

수정하지 않은 기존 분석 함수에는 명시적인 단일 프로세스 offline context를 사용할 수 있다.

```python
from nomad_storage_sdf.loader import restoring_numpy_load
with restoring_numpy_load():
    original_snapshot = Snapshot.load(path)
```

이 context는 값이 빠진 SDF NPZ에만 NpzFile 읽기 인터페이스를 제공하고 종료 시 np.load를 복원한다. **전역 설치·sitecustomize·frozen runtime 수정은 없다. 온라인에서 자동 활성화하지 않는다.** plain `np.load`에는 여전히 values key가 없으므로 새 loader/context 없이 예전 분석을 직접 실행하면 해당 key 접근이 실패할 수 있다.

Phase31-E 원 분석 스크립트 SHA256 `{before['original_analysis_sha256']}`에서 필요한 계산 함수만 **동일한 함수 본문**으로 새 검증 도구에 보존했다. 기존 결과 디렉터리/문서에 report를 다시 쓰지 않고 이 pilot의 기존 충돌 사례 계산만 수행했다.

{table(agreement)}

`box_history`의 다른 모든 반환값도 그대로다(관측 칸 수·최초 시각·공개 시각·snapshot 참조 등). [phase31e_before.json](../research/results/storage_retrofit/phase31e_before.json)과 [phase31e_after.json](../research/results/storage_retrofit/phase31e_after.json)이 정확히 일치한다. 이어 모든93개 파일의 복원 dict를 tar 원본과 직접 대조하여1,116개 배열이 bit-exact임을 검증했다.

## 4. 원래 input hash 추적

- [manifest.json](../research/results/storage_retrofit/manifest.json): 파일별 원/새 SHA256, values bit 일치, 배열별 fingerprint, 크기 전후, 원본 tar/member, literal 복원 검산.
- [conversion_manifest.csv](../research/results/storage_retrofit/conversion_manifest.csv): 위 핵심 열의 평면 표.
- [conversion_journal.jsonl](../research/results/storage_retrofit/conversion_journal.jsonl): atomic 교체 전후 기록.
- [report_hash_lineage.json](../research/results/storage_retrofit/report_hash_lineage.json): Phase31-D {sum('phase31d' in r['report_manifest'] for r in refs)}개, Phase31-E {sum('phase31e' in r['report_manifest'] for r in refs)}개, Phase32-O {sum('phase32o' in r['report_manifest'] for r in refs)}개 기존 hash 참조 검증.

```python
from nomad_storage_sdf.loader import resolve_original_hash
proof = resolve_original_hash(path, old_sha256, manifest_path)
```

현재 파일 SHA가 manifest의 new SHA와 같은지 확인하고, 원 SHA가 old SHA인지 대조한 다음 복원 배열을 검사한다. 원 보고서의 input hash를 새 SHA로 덮어쓰거나, 현재 NPZ bytes가 원 bytes와 같다고 주장하지 않는다. 원 zip bytes의 복구 경로가 backup_tar/member로 남는다. **원 SHA를 직접 검사하는 frozen 스크립트의 audit는 별도 manifest-aware 확인이 필요**하다. np.load context는 배열 복원만 담당하며 SHA 검사를 우회하지 않는다.

## 5. SSD 전체 지정 범위의 읽기 전용 추정

인벤토리는 pilot 변환 전에 취득했다. 아래 **{len(inventory):,}개 target NPZ, {sum(r['bytes'] for r in inventory)/1e9:.3f}GB**가 범위다. 원 depth NPZ는 {len(raw):,}개 / {sum(r['bytes'] for r in raw)/1e9:.3f}GB이며 변환/절감 대상에 넣지 않는다. phase28t smoke/main을 phase28 prefix에 포함했다. phase32 및 그 외 이전 phase는 이 추정에 포함하지 않았다.

{table(whole_table)}

root × snapshot/input × ZIP 저장 형식으로 층화하고 seed20261107로 층당최대3개, 총 **{len(samples)}개**를 읽어 실제 재압축 크기를 측정했다. 표본 values 일치는 **{sum(r['bit_equal'] for r in samples)}/{len(samples)}**였다. 층별 `Σ새크기/Σ원크기` 비율을 해당 층 전체 크기에 적용한 점추정은 **{predicted/1e9:.3f}GB 절감**, 나머지 target 크기 약 **{sum(r['estimated_after_bytes'] for r in est)/1e9:.3f}GB**다. 같은 표본의 최소/최대 압축비로 본 민감도 범위는 **{low/1e9:.3f}~{high/1e9:.3f}GB**이며 통계적95% 신뢰구간이 아니다.

이 수치에는 이번 pilot도 포함돼 있다. 이미 절감한 {saved/1e9:.3f}GB를 제외한 추가 절감은 대략 {(predicted-saved)/1e9:.3f}GB 수준이다. **미검사 파일 전체의 bit 일치를 보장한 값이 아니며**, 실제 bulk 적용 시에도 각각 재계산·비트 검증과 백업을 먼저 해야 한다. 다른 run을 변환하지 않았다.

세부: [ssd_summary.csv](../research/results/storage_retrofit/ssd_summary.csv), [ssd_estimates.json](../research/results/storage_retrofit/ssd_estimates.json), [ssd_compression_samples.json](../research/results/storage_retrofit/ssd_compression_samples.json), [ssd_inventory.json](../research/results/storage_retrofit/ssd_inventory.json).

## 재검증 명령 및 종료 상태

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research OPENBLAS_NUM_THREADS=1 /usr/bin/python3 -m nomad_storage_sdf.pilot --stage verify`

문서 재생성: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_storage_sdf.report`

현재 상태: 지정 run 변환·복원·Phase31-E 검증 완료. **여기서 멈추며 SSD 전체 변환은 실행하지 않는다.** venv pip install 없음. 새 도구·manifest·문서만 commit/push한다.
'''
 (ROOT/'docs/STORAGE_RETROFIT.md').write_text(text)
 print(json.dumps({k:summary[k] for k in ('total_target_files','converted','bit_equal_fraction','target_before_bytes','target_after_bytes','saved_ssd_bytes','wide_estimated_saved_bytes','phase31e_equal')}))

if __name__=='__main__':main()
