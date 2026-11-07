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

<!-- STORAGE_RETROFIT_BULK -->

# 후속 SSD 전체 변환 — 사용자 재개 요청

**상태: COMPLETE**. 새 시뮬레이션/추론/Graph solve0. frozen 실험 코드·이전 결과 문서를 변경하지 않았다. 이 절만 기존 STORAGE_RETROFIT 문서 뒤에 추가했다.

## 중단 후 선행 점검

- 발견 임시 파일: 1개. 원본 NPZ의 CRC/배열/finiteness/SDF 일치를 확인한 후0바이트 `phase24r_pilot_01/main/SLW_144_G/g_jobs/snapshot_0104.npz.archive.tmp`만 삭제했다. 원본SHA는 그대로다.
- 기존 pilot 변환93개를 새 SHA와 복원 배열 fingerprint로 재검증했다. 손상 발견0, 부분 manifest 보정 필요 0개. 원래 pilot 증거는 보존했다.
- [resume_audit.json](../research/results/storage_retrofit_bulk/resume_audit.json)에 파일별 점검 결과가 있다.

## 범위·실행 보호

`../artifacts/isaac6`의 run-root 전부를 조사하되 파일 종류는 원 절차와 같은 **depth/snapshot_*.npz, repair_jobs/input_*.npz**만이다. 원 depth_*.npz·g_jobs snapshot·cache NPZ 등은 변환하지 않는다. 이번 조사 135개 root 중 대상이 있는 root 27개, 대상 파일 151,772개다. 새로 생긴 root를 실행 도중 범위에 추가하지 않는다.

호스트 PID/state.json·실제 kernel lock·열린 file descriptor를 확인한다. 실행용 root lock marker나 실제 점유 lock이 있으면 제외한다. 종료 뒤 남은 `cache/ov/_cache.lock` 같은 라이브러리 캐시 파일은 **실제 점유가 없는지 확인하고 보존**하며, 지우지 않는다. `phase32_01`은 명시적으로 보호한다. 논리 CPU16개 중2개를 남겨14개 worker **프로세스**로 전환했으며 `nice -n 10`을 적용한다. worker마다 독립 파일을 소유하고 검증→원자 교체→worker별 journal을 기록한 뒤 root manifest로 병합한다. 공유 abort 신호와 교체 lock으로 오류 이후 추가 교체를 막는다. 메모리 여유4GiB 미만 또는 시작 기준보다 swap 점유 증가/새 swap-out이 감지되면 현재 파일을 마치고8개로 축소한다. 시작 전부터 점유된 swap은 새 사용과 구분해 보고한다. 실제 IO 오류에도 자동 재시도하지 않는다.

진행 heartbeat가180초 넘게 끊기면 다음 변환 batch 전에 PAUSED_NO_HEARTBEAT로 멈춘다(ESC/연결 중단 대비). 현재 backup은 완성·검증할 수 있지만 그 뒤 원본 변환을 시작하지 않는다. SIGINT/SIGTERM도 상태와 journal을 남긴다. 멈춘 원본을 숨기거나 성공으로 간주하지 않는다.

## 백업·버전·파일 검증

작은 run-root부터, 그 안에서도 작은 run부터 처리한다. **백업 중단 지시 전에는** 각 run 전체를 One Touch `/media/gpuadmin/One Touch/nomad_archive/backup_before_sdf_strip/bulk_20261107T094127Z`에 tar로 보존하고 원본 regular-file SHA를 tar member와 대조한 뒤 변환했다. 현재 검증된 backup 47개, tar 111.646GB다. 각 tar 옆 `.inventory.json`에는 원본 전체 파일의 hash·metadata가 있고, root별 `backups/`에는 영수증이 있다. 기존 backup은 삭제하지 않으며, 중단 이후 정책과 계측은 아래 절에 따로 기록한다. 이전 pilot의 원래 zip bytes는 기존 H1 tar로 계속 추적한다.

각 run provenance의 git commit/기록 source SHA를 사용해 그 당시 `LogOddsSDF.update`와 `DepthSDF.__init__` 버전을 확인한다. 지원하는 frozen AST와 같을 때만 runtime EDT 복원을 허용하며 **실제 파일마다 values bytes 일치가 추가로 필수**다. 알려지지 않은 버전/형식은 원본 그대로 사유를 기록한다. [versions.json](../research/results/storage_retrofit_bulk/versions.json)에 함수 버전 근거가 있다.

원 파일을 읽어 original SHA를 확보하고(백업 단계에서는 백업 목록과도 대조), 같은 함수로 values를 계산한다. 일치하는 경우에만 임시 NPZ를 만들고 복원 로더로 **모든 원 배열을 직접 byte 비교**한다. 임시 파일 fsync 후 PREPARED 기록을 fsync하고, 원본이 바뀌지 않았음을 다시 확인한 뒤 `os.replace`한다. 불일치는 원본을 그대로 둔다. 변환 후 파일 SHA도 다시 확인한다. `arrays_sha256`은 모든 배열의 dtype/shape/order/bytes fingerprint를 정렬한 전체 digest다.

폴더별 `manifest.jsonl`과 `journal.jsonl`에 original/new SHA, 검증 결과, 크기, 원본 tar/member, runtime version을 기록한다. 이미 축소된93개는 복원 검증 후 ALREADY_COMPACT로 건너뛰며 이번 절감량에 다시 넣지 않는다. 원 input hash는 manifest-aware `resolve_original_hash`로 추적해야 하며 frozen 보고서의 hash를 덮어쓰지 않는다.

## run-root별 결과

| run-root | 상태 | 처리 대상 | 신규 변환 | bit 검사/일치 | 일치율 | skip(사유) | 폴더 GB 전→후 | 절감 GB |
|---|---|---|---|---|---|---|---|---|
| phase28t_smoke_01 | COMPLETE | 10 | 10 | 10/10 | 100.00% | {} | 0.093→0.016 | 0.077 |
| phase15b_socket_smoke_01 | COMPLETE | 111 | 111 | 111/111 | 100.00% | {} | 1.149→0.666 | 0.482 |
| phase18_preflight_03 | COMPLETE | 118 | 116 | 118/116 | 98.31% | {"SKIPPED_SDF_MISMATCH": 2} | 1.269→0.575 | 0.694 |
| phase20_so_smoke_01 | COMPLETE | 117 | 117 | 117/117 | 100.00% | {} | 1.464→0.570 | 0.893 |
| phase20b_check_L3_01 | COMPLETE | 118 | 118 | 118/118 | 100.00% | {} | 1.505→0.569 | 0.936 |
| phase20b_check_L2_01 | COMPLETE | 118 | 118 | 118/118 | 100.00% | {} | 1.534→0.571 | 0.963 |
| phase28t_smoke_02 | COMPLETE | 170 | 170 | 170/170 | 100.00% | {} | 1.834→0.154 | 1.680 |
| phase28t_main_01 | COMPLETE | 1984 | 1984 | 1984/1984 | 100.00% | {} | 22.670→2.966 | 19.704 |
| phase30r_dev_01 | COMPLETE | 1905 | 1905 | 1905/1905 | 100.00% | {} | 23.997→3.637 | 20.360 |
| phase20_so_01 | COMPLETE | 3322 | 3322 | 3322/3322 | 100.00% | {} | 30.608→7.154 | 23.454 |
| phase20b_blockage_01 | COMPLETE | 3445 | 3445 | 3445/3445 | 100.00% | {} | 32.019→6.079 | 25.940 |
| phase20e_obstacle_01 | COMPLETE | 3794 | 3794 | 3794/3794 | 100.00% | {} | 37.700→8.395 | 29.305 |
| phase28_pilot_01 | COMPLETE | 3379 | 3379 | 3379/3379 | 100.00% | {} | 38.121→4.555 | 33.566 |
| phase20f_new_obstacle_01 | COMPLETE | 3958 | 3958 | 3958/3958 | 100.00% | {} | 38.363→8.150 | 30.213 |
| phase20d_recent_01 | COMPLETE | 3909 | 3909 | 3909/3909 | 100.00% | {} | 39.872→9.289 | 30.583 |
| phase22_refine_drive_01 | COMPLETE | 5328 | 5328 | 5328/5328 | 100.00% | {} | 44.185→2.164 | 42.021 |
| phase26_smoke_01 | COMPLETE | 4052 | 4052 | 4052/4052 | 100.00% | {} | 47.571→11.607 | 35.963 |
| phase31p_01 | COMPLETE | 3398 | 3398 | 3398/3398 | 100.00% | {} | 47.756→7.951 | 39.805 |
| phase24r_pilot_01 | COMPLETE | 3885 | 3885 | 3885/3885 | 100.00% | {} | 64.917→25.954 | 38.963 |
| phase15b_depth_02 | COMPLETE | 8965 | 8965 | 8965/8965 | 100.00% | {} | 67.959→32.338 | 35.621 |
| phase27r_pilot_01 | COMPLETE | 8827 | 8827 | 8827/8827 | 100.00% | {} | 84.048→6.178 | 77.870 |
| phase21_baseline_01 | COMPLETE | 13088 | 13088 | 13088/13088 | 100.00% | {} | 103.223→4.922 | 98.300 |
| phase26_pilot_01 | COMPLETE | 11298 | 11298 | 11298/11298 | 100.00% | {} | 108.125→7.356 | 100.770 |
| phase29_01 | COMPLETE | 10924 | 10831 | 10924/10924 | 100.00% | {"ALREADY_COMPACT": 93} | 126.177→17.984 | 108.194 |
| phase16_multiscene_01 | COMPLETE | 13491 | 13335 | 13491/13335 | 98.84% | {"SKIPPED_SDF_MISMATCH": 156} | 128.550→47.693 | 80.857 |
| phase17_multiscene_01 | COMPLETE | 18336 | 18114 | 18336/18114 | 98.79% | {"SKIPPED_SDF_MISMATCH": 222} | 173.386→65.670 | 107.716 |
| phase18_confirm_01 | COMPLETE | 23722 | 23434 | 23722/23434 | 98.79% | {"SKIPPED_SDF_MISMATCH": 288} | 223.804→84.338 | 139.466 |

대상 없는 root와 제외 root까지 포함한 전체 목록: [root_summary.csv](../research/results/storage_retrofit_bulk/root_summary.csv). 신규 변환 **151,011개**, 이번 SSD 절감 **1124.396GB**. SKIPPED_UNKNOWN_VERSION/DIFFERENT_FORMAT/SDF_MISMATCH/ALREADY_COMPACT는 서로 구분한다. bit 일치율의 분모는 실제 재계산·복원 비교를 수행한 파일이며 형식/버전 미상 파일을 PASS로 채우지 않는다.

오류: `없음`. 원본 손상이 발견되거나 예외가 발생하면 이후 파일/폴더로 진행하지 않는다. STOPPED_ERROR는 사용자 검토 없이 다시 시작하지 못한다.

## 변환 후 df

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p1  1.9T  666G  1.1T  38% /home/gpuadmin/Workspace/NoMaD
/dev/sda1       1.9T  564G  1.3T  31% /media/gpuadmin/One Touch
```

Byte 단위 df와 집계: [summary.json](../research/results/storage_retrofit_bulk/summary.json). root마다 완료 시점 df도 해당 `summary.json`에 저장한다. 외장 백업은 삭제하지 않는다.


## 프로세스 병렬 전환과 처리 속도

전환 전 단일 Python 프로세스(파일 검증 thread4→7)의 전체 경과시간 기준: 6,456개 / 28.48분 = **226.67파일/분**, 평균 **0.2647초/파일**. 백업·검증·중간 일시정지가 포함된다. 재조사 대상151,772개 중 이미 처리6,456개, 기존 pilot 축소93개를 제외한 남은 변환 후보는 **145,223개**다. 이 속도를 적용한 예상 잔여시간은 **10.68시간**이며 파일 크기/백업 비중에 따라 달라진다.

전환 후 첫 300.4초(프로세스 시작·백업 포함): **423.09파일/분**, 처리 2,118개, 예상 잔여 **5.64시간**. 측정 시 worker 14개. 시스템 사용 메모리 최대(MemTotal−MemAvailable) **9.86GiB**, worker RSS 합 최대 **2.11GiB**, 메모리 여유 최소 **20.63GiB**. 기존 swap 점유 **5.99GiB**; worker 축소 기록: `[]`. RSS 합은 공유 메모리를 중복 집계할 수 있다. [측정 원자료](../research/results/storage_retrofit_bulk/parallel_5min.json).

## 사용자 지시: 추가 One Touch 백업 중단

실제 백업 단위는 파일별이 아니라 run 전체 tar였다. 사용자 지시 이후 **추가 백업0**으로 전환했다. 기존 tar 47개 **111.646GB**, 목록 포함 **111.712GB**를 그대로 유지한다. 삭제0, 중단 시 부분 tar 0개. 첫 H1 pilot 백업도 보존한다. [기존 백업 전체 목록](../research/results/storage_retrofit_bulk/backup_inventory_at_disable.json).

새 파일은 원본 bytes에서 SHA와 모든 배열 fingerprint를 먼저 확보한다. 임시 파일을 압축한 뒤 복원 로더의 모든 배열을 원본과 직접 bit 비교하고, 원본 SHA가 바뀌지 않았는지 다시 확인한 뒤에만 원자 교체한다. 압축 수준·비트 검증을 변경하거나 생략하지 않았다. manifest의 backup_tar=null은 이 정책 이후의 파일을 뜻하며, 과거 원본 ZIP SHA를 manifest lineage로 추적한다.

## 백업 중단 후 1분 단계별 계측

60.17초, 완료 파일 1165개. 모든 값은 worker별 wall-clock 누적이며, 병렬 실행 때문에 합계는 실경과보다 크다. 재계산이 복원 로더 안에서 실행된 시간은 read에서 빼 SDF에 분류했다. bit 검증에는 배열 fingerprint·원본/임시/교체 후 SHA 확인을 포함한다. manifest는 journal flush/fsync를 포함한다. One Touch backup은 사용자 지시로 측정 전에 중단됐으므로0이다.

| 단계 | worker 초 합 | 비중 |
|---|---|---|
| read_decompress | 83.962 | 10.38% |
| sdf_recompute | 284.985 | 35.22% |
| bit_validation | 80.232 | 9.91% |
| compress_save | 27.381 | 3.38% |
| atomic_replace | 1.267 | 0.16% |
| one_touch_backup | 0.0 | 0.00% |
| manifest | 2.964 | 0.37% |
| guard | 48.839 | 6.04% |
| lock_wait | 275.929 | 34.10% |
| other | 3.663 | 0.45% |

| worker | pid | 파일 | read_decompress | sdf_recompute | bit_validation | compress_save | atomic_replace | one_touch_backup | manifest | guard | lock_wait | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2233066 | 83 | 5.7773 | 21.126 | 5.6889 | 1.9968 | 0.0787 | 0.0 | 0.1878 | 3.0752 | 19.6776 | 0.2606 |
| 1 | 2233059 | 83 | 5.7279 | 20.7086 | 5.9281 | 1.8246 | 0.0919 | 0.0 | 0.2159 | 3.3925 | 19.8948 | 0.2723 |
| 2 | 2233064 | 83 | 6.2557 | 20.6211 | 5.7182 | 2.0148 | 0.0946 | 0.0 | 0.2085 | 3.1074 | 19.413 | 0.246 |
| 3 | 2233052 | 83 | 6.55 | 20.1806 | 6.124 | 2.0638 | 0.1194 | 0.0 | 0.3185 | 3.3079 | 19.1038 | 0.2925 |
| 4 | 2233055 | 82 | 5.8158 | 20.1011 | 5.6063 | 1.9459 | 0.0941 | 0.0 | 0.1984 | 4.0413 | 19.5548 | 0.263 |
| 5 | 2233062 | 83 | 5.5822 | 20.2962 | 5.5919 | 1.8543 | 0.0755 | 0.0 | 0.1726 | 4.1363 | 20.0899 | 0.2498 |
| 6 | 2233057 | 83 | 5.61 | 21.1315 | 5.4967 | 1.871 | 0.0725 | 0.0 | 0.1773 | 3.1884 | 19.8494 | 0.2383 |
| 7 | 2233056 | 83 | 6.1585 | 20.3065 | 5.4292 | 1.9887 | 0.089 | 0.0 | 0.201 | 3.3897 | 19.7055 | 0.2459 |
| 8 | 2233058 | 83 | 6.1476 | 19.2212 | 5.7761 | 2.1087 | 0.0813 | 0.0 | 0.1949 | 3.3194 | 19.8288 | 0.2777 |
| 9 | 2233061 | 85 | 6.4706 | 20.4561 | 6.051 | 1.824 | 0.1036 | 0.0 | 0.2491 | 3.8768 | 18.9679 | 0.2664 |
| 10 | 2233065 | 84 | 6.1725 | 20.6163 | 5.7589 | 1.9852 | 0.0919 | 0.0 | 0.1944 | 3.1271 | 20.1553 | 0.2461 |
| 11 | 2233060 | 82 | 5.4724 | 20.2364 | 5.692 | 2.0647 | 0.0725 | 0.0 | 0.1643 | 2.9671 | 20.7491 | 0.2829 |
| 12 | 2233063 | 83 | 5.9897 | 20.6217 | 5.6196 | 1.831 | 0.0847 | 0.0 | 0.2136 | 3.5093 | 19.7389 | 0.2496 |
| 13 | 2233067 | 85 | 6.2323 | 19.362 | 5.7514 | 2.0077 | 0.1169 | 0.0 | 0.2679 | 4.4004 | 19.2003 | 0.2717 |

## 백업 없는 5분 처리량

300.55초에 5,630개: **1123.95파일/분**, 파일당 0.0534초. 백업 포함 병렬 대비 2.66배. 남은 후보 135,338개, 예상 **2.01시간**. worker 14개; worker RSS 합 최대 2.59GiB, 시스템 사용 최대 10.54GiB, 여유 최소 19.95GiB. worker 변경: `[]`. 파일 구성과 저장장치 상태가 달라질 수 있는 관측 추정이며 확정 완료시각은 아니다.

추가 백업 제거 뒤 처리량이 크게 늘어 백업이 주요 병목이었던 것으로 판단한다. 동일 파일을 반복한 통제 비교는 아니다. 백업 없는 1분 계측에서 가장 큰 작업은 SDF 재계산이고, 전역 교체 lock 대기도 크다. **제안만**: 모든 검증을 유지하면서 독립적인 읽기·SHA 확인을 전역 lock 밖으로 분리하고, lock은 오류 플래그 확인·durable PREPARED·원자 교체 구간에 한정하는 방안을 별도로 검증할 수 있다. 이번에는 적용하지 않았으며 압축 수준과 비트 검증은 그대로다.

## 전체 실행의 메모리 감시

0.25초 간격 관측 최대: worker RSS 합 2.64GiB, 시스템 사용 10.77GiB. 여유 최소 19.72GiB. 위 5분 측정 시점은14 worker였으나 **측정 이후 새 swap-out을 감지해8 worker로 자동 축소**했다. 이후 재개도8개를 유지한다. 전환 이력은 [memory_history.json](../research/results/storage_retrofit_bulk/memory_history.json)에 보존한다. 재개 시 worker 수를14로 잘못 가정한 검사와 짧은 재기동 이력도 [resume_control_note.json](../research/results/storage_retrofit_bulk/resume_control_note.json)에 기록했다. 파일 변환 예외나 손상은 발생하지 않았다. 현재/종료 설정: 8 worker.

## 최종 감사

**PASS**: manifest 전체 범위·중복 소유권·manifest SHA·파일 크기 확인, 잔여 변환 임시 파일 0개. frozen 실험 source 변경 0개, 기존 결과 문서 변경 0개. 백업 중단 뒤 추가/변경/삭제된 백업 파일 0개. 이미 수행한 파일별 원본/임시 배열 bit 비교와 교체 후 SHA 검증 기록을 감사했으며, 전체 EDT를 불필요하게 다시 실행하지 않았다.

Phase31-E 회귀: PASS=True, 상자 최초 관측 기록 동일=True, 계획 depth clearance bit 일치=True, oracle clearance bit 일치=True. [최종 감사 원자료](../research/results/storage_retrofit_bulk/final_audit.json).

절감량은 대상 NPZ의 논리적 파일 크기 차이다. `df`는 블록 할당·새 manifest 저장·다른 파일시스템 사용도 포함하므로 완전히 같은 값은 아니다.


상태 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_storage_sdf.bulk --status`

문서 재집계: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_storage_sdf.bulk_report`
