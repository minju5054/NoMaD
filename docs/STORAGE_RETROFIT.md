# Storage retrofit — 한 run SDF values 제거·복원 검증

**완료 범위: `phase29_01/dev/H1_201_G18/attempt1` 한 run만.** 새 시뮬레이션·추론·Graph 풀이·패키지 설치0. frozen 실험 코드·기존 결과 문서는 변경하지 않았다. 다른 run은 읽기 전용 용량 추정만 했다.

- snapshot **90개** + repair input **3개** = **93개**, values 재계산 비트 일치 **93/93 (100%)**. 모두 변환, 건너뜀0.
- 대상 NPZ **969.450978MB → 9.688900MB**, SSD 논리 크기 **959.762078MB (99.00%) 절감**. 할당 block 기준 절감 959.750144MB.
- 복원한 **1116개 배열**을 tar 원본 배열과 직접 byte 비교해 모두 일치했다(values 포함, dtype/shape/Fortran order 보존).
- Phase31-E 최초 상자 관측 및 계획 여유 계산 동일. 기존 input hash 참조 **28개**가 old SHA→new SHA→원본 tar member로 검증됐다.
- SSD 지정 범위 전체에 같은 방식을 적용하면 **약 337.2GB 절감 예상**. 이는 표본 기반 추정이며 bulk 변환은 실행하지 않았다.

## 1. 백업 → dry-run/변환 → 복원 검증

실제 순서는 읽기 전용 dry-run → 원본 run 전체 tar 백업 및검증 → 해당93개만 atomic 교체 → 복원/기존 분석 검산이다. 백업은 **변환 전에** 완료했다.

백업 파일:

`/media/gpuadmin/One Touch/nomad_archive/backup_before_sdf_strip/phase29_01_dev_H1_201_G18_attempt1_20261107T075310Z.tar`

- tar 크기: **1,058,467,840bytes (1.058468GB)**.
- SHA256: `c68db086aeaa5be2fe946709dff2b5675a8887c9801049ec1fc964314484f72a`.
- run의 정규 파일 **487개 전부** tar member SHA256이 원본과 같음을 확인했다. 디렉터리 포함 검증 member 519개.
- 같은 One Touch 폴더의 `.tar.inventory.json`은 원본 파일별 SHA256/크기/mtime/mode 목록이다. SSD 쪽 [backup.json](../research/results/storage_retrofit/backup.json)과 [run_inventory_before.json](../research/results/storage_retrofit/run_inventory_before.json)에도 영수증과 목록을 보존했다.
- 원본 run의 정규 파일 총합은 1.057526GB → 0.097764GB다. tar 백업은 SSD가 아닌 One Touch 공간을 사용한다. 전체 저장장치 사용량이 그만큼 줄었다는 뜻은 아니다.

단위테스트6개 통과: bit-exact round trip(NaN payload/negative zero/Fortran 배열 포함),1ULP values 차이 시 원파일 미변경, 기존 Snapshot.load의 opt-in 복원, empty grid, hash 변조 거부, dry-run 이후 원본 변경 시 변환 거부.

## 2. 정확히 무엇을 바꿨는가

대상 패턴은 **`depth/snapshot_*.npz`와 `repair_jobs/input_*.npz`만**이다(`snapshot_initial.npz` 포함). `depth/depth_*.npz`, `depth/final.npz`, cache NPZ, RGB, CSV, JSON/JSONL 로그와 그 외 run 파일은 원본 SHA256이 유지됐다. 변환 대상으로 지정한93개 이외 정규 파일 394개가 그대로다.

| 종류 | 파일 수 | 이전 bytes | 이후 bytes | 이전 MB | 이후 MB | 절감 MB |
|---|---|---|---|---|---|---|
| depth/depth_*.npz(원 depth) | 89 | 3511728 | 3511728 | 3.511728 | 3.511728 | 0.000000 |
| depth/snapshot_*.npz | 90 | 848113902 | 9237295 | 848.113902 | 9.237295 | 838.876607 |
| repair_jobs/input_*.npz | 3 | 121337076 | 451605 | 121.337076 | 0.451605 | 120.885471 |

values는 현재 런타임의 `nomad_phase15.occupancy.distance_transform_edt`를 그대로 호출해 `distance_transform_edt(~occupied, sampling=h) - radius`로 계산한다. 별도 EDT·근사·float16 변환·양자화가 없다. empty grid는 origin/h/shape로 범위를 복원해 원 `DepthSDF`의 empty-distance 계산을 사용한다. 저장되지 않은 실제 bound의 부동소수 반올림 때문에 일치하지 않는 파일은 **values를 포함한 원 NPZ 전체를 그대로 둔다**. 이번93개는 empty grid까지 모두 일치했다.

매 파일에서 dtype·shape·배열의 모든 bit가 같은 경우에만 values를 제외하고 `np.savez_compressed`로 다시 쓴다. 나머지 배열의 dtype/order/내용을 보존하고, 같은 디렉터리 임시 파일을 fsync·복원 검증한 후 atomic replace한다. `original_sha256/new_sha256`의 PREPARED 기록을 교체 전에 fsync하여 중단되어도 대응을 추적할 수 있다. mismatch 파일은 압축만 다시 하는 것도 하지 않는다. 파일 mode/mtime도 유지했다.

현재 검증 환경: Python 3.12.3, NumPy 1.26.4, SciPy 1.11.4, zlib 1.3. 원 런타임 함수 소스 hash는 [dry_run.json](../research/results/storage_retrofit/dry_run.json)에 고정했다. 다른 환경으로 옮겨 재계산할 때도 manifest의 배열 fingerprint 검증을 통과해야 한다.

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

Phase31-E 원 분석 스크립트 SHA256 `54c2d6aed3c1c07e33c9a61b8dc75139a4ee4973d134cfab1564b2d71df197cf`에서 필요한 계산 함수만 **동일한 함수 본문**으로 새 검증 도구에 보존했다. 기존 결과 디렉터리/문서에 report를 다시 쓰지 않고 이 pilot의 기존 충돌 사례 계산만 수행했다.

| Phase31-E 지표 | 변환 전 | 변환 후 | 검증 |
|---|---|---|---|
| 상자 최초 occupied capture(s) | 18.48611111111111 | 18.48611111111111 | 정확 일치 |
| 최초 snapshot 발행(s) | 18.625971563156202 | 18.625971563156202 | 정확 일치 |
| 계획 base-depth exact 여유(m) | 0.13265061928492003 | 0.13265061928492003 | float64 bytes 일치 |
| 계획 oracle 여유(m, 평가만) | 0.14229571198483063 | 0.14229571198483063 | float64 bytes 일치 |

`box_history`의 다른 모든 반환값도 그대로다(관측 칸 수·최초 시각·공개 시각·snapshot 참조 등). [phase31e_before.json](../research/results/storage_retrofit/phase31e_before.json)과 [phase31e_after.json](../research/results/storage_retrofit/phase31e_after.json)이 정확히 일치한다. 이어 모든93개 파일의 복원 dict를 tar 원본과 직접 대조하여1,116개 배열이 bit-exact임을 검증했다.

## 4. 원래 input hash 추적

- [manifest.json](../research/results/storage_retrofit/manifest.json): 파일별 원/새 SHA256, values bit 일치, 배열별 fingerprint, 크기 전후, 원본 tar/member, literal 복원 검산.
- [conversion_manifest.csv](../research/results/storage_retrofit/conversion_manifest.csv): 위 핵심 열의 평면 표.
- [conversion_journal.jsonl](../research/results/storage_retrofit/conversion_journal.jsonl): atomic 교체 전후 기록.
- [report_hash_lineage.json](../research/results/storage_retrofit/report_hash_lineage.json): Phase31-D 1개, Phase31-E 2개, Phase32-O 25개 기존 hash 참조 검증.

```python
from nomad_storage_sdf.loader import resolve_original_hash
proof = resolve_original_hash(path, old_sha256, manifest_path)
```

현재 파일 SHA가 manifest의 new SHA와 같은지 확인하고, 원 SHA가 old SHA인지 대조한 다음 복원 배열을 검사한다. 원 보고서의 input hash를 새 SHA로 덮어쓰거나, 현재 NPZ bytes가 원 bytes와 같다고 주장하지 않는다. 원 zip bytes의 복구 경로가 backup_tar/member로 남는다. **원 SHA를 직접 검사하는 frozen 스크립트의 audit는 별도 manifest-aware 확인이 필요**하다. np.load context는 배열 복원만 담당하며 SHA 검사를 우회하지 않는다.

## 5. SSD 전체 지정 범위의 읽기 전용 추정

인벤토리는 pilot 변환 전에 취득했다. 아래 **34,649개 target NPZ, 342.763GB**가 범위다. 원 depth NPZ는 17,369개 / 0.587GB이며 변환/절감 대상에 넣지 않는다. phase28t smoke/main을 phase28 prefix에 포함했다. phase32 및 그 외 이전 phase는 이 추정에 포함하지 않았다.

| 범위 | snapshot 수 | snapshot GB | input 수 | input GB | 원 depth 수 | 원 depth GB | 예상 절감 GB |
|---|---|---|---|---|---|---|---|
| phase26_smoke_01 | 3987 | 33.921 | 65 | 2.629 | 3973 | 0.139 | 35.993 |
| phase27r_pilot_01 | 8693 | 73.580 | 134 | 5.419 | 5725 | 0.204 | 77.674 |
| phase28_pilot_01 | 3212 | 27.255 | 167 | 6.753 | 2496 | 0.075 | 33.768 |
| phase28t_main_01 | 1887 | 16.048 | 97 | 3.923 | 1291 | 0.037 | 19.789 |
| phase28t_smoke_01 | 10 | 0.077 | 0 | 0.000 | 9 | 0.000 | 0.077 |
| phase28t_smoke_02 | 167 | 1.581 | 3 | 0.121 | 166 | 0.007 | 1.680 |
| phase29_01 | 10319 | 86.160 | 605 | 24.466 | 2734 | 0.092 | 107.921 |
| phase30r_dev_01 | 1761 | 14.793 | 144 | 5.823 | 975 | 0.034 | 20.421 |
| phase31p_01 | 3040 | 25.739 | 358 | 14.476 | 0 | 0.000 | 39.860 |

root × snapshot/input × ZIP 저장 형식으로 층화하고 seed20261107로 층당최대3개, 총 **51개**를 읽어 실제 재압축 크기를 측정했다. 표본 values 일치는 **51/51**였다. 층별 `Σ새크기/Σ원크기` 비율을 해당 층 전체 크기에 적용한 점추정은 **337.184GB 절감**, 나머지 target 크기 약 **5.579GB**다. 같은 표본의 최소/최대 압축비로 본 민감도 범위는 **334.425~340.026GB**이며 통계적95% 신뢰구간이 아니다.

이 수치에는 이번 pilot도 포함돼 있다. 이미 절감한 0.960GB를 제외한 추가 절감은 대략 336.224GB 수준이다. **미검사 파일 전체의 bit 일치를 보장한 값이 아니며**, 실제 bulk 적용 시에도 각각 재계산·비트 검증과 백업을 먼저 해야 한다. 다른 run을 변환하지 않았다.

세부: [ssd_summary.csv](../research/results/storage_retrofit/ssd_summary.csv), [ssd_estimates.json](../research/results/storage_retrofit/ssd_estimates.json), [ssd_compression_samples.json](../research/results/storage_retrofit/ssd_compression_samples.json), [ssd_inventory.json](../research/results/storage_retrofit/ssd_inventory.json).

## 재검증 명령 및 종료 상태

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research OPENBLAS_NUM_THREADS=1 /usr/bin/python3 -m nomad_storage_sdf.pilot --stage verify`

문서 재생성: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_storage_sdf.report`

현재 상태: 지정 run 변환·복원·Phase31-E 검증 완료. **여기서 멈추며 SSD 전체 변환은 실행하지 않는다.** venv pip install 없음. 새 도구·manifest·문서만 commit/push한다.
