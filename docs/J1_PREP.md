# J1 사전 등록

| passed | tests | launcher_dry_runs | main_runs_started | protocol_sha256 | disk_free_bytes |
| --- | --- | --- | --- | --- | --- |
| True | 6 | 195 | 0 | 2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586 | 1072193822720 |

SLW-v2·H1-v3·LC × seed231–243 ×5방법=195회. 15회 seed블록 안 순서만 RNG20261112로 섞고, 5.5h 이후 새seed블록을 시작하지 않는다. 진행 중 블록은 끝내고 중간 결과를push하며 동일 명령으로 재개한다. 본 실행은 원래 저장소 cwd에서만 허용한다.

LC는 J0 통과. H1-v3·SLW-v2는 미달이나 돌발 장애물·좁은 통로 평가용으로 사전 포함. scene·Topomap·선별결과 hash를 protocol에 기록했다.

| scene | axis | direction | box_id | dynamic | threshold_m | formula |
| --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | 0 | 1 | Slalom3 | False | 4.6 | last box +x far face +0.30; identical to SLW |
| H1-v3 | 1 | 1 | DynamicObstacle | False | 1.2 | box center along +y + projected half extent + 0.30 |
| LC | 1 | 1 | AfterCorner | False | 2.4 | box center along axis + projected half extent + 0.30 |

실행기는 Phase18 PP/CURV이고 목표0.3m 참위치 종료, 공식NoMaD argmin closest/subgoal·1s 만료·지연보정·V1 depth·SDF fix·ENDPOINT latch 공통이다. 회복·STOP_WAIT 특수처리·HMM/NET은 없다. OURS-noEC는 기존 J0 객체 그대로다. RAW는 Phase18-RAW 재사용+공통latch,RTC는 Phase18 생성/SAFE를 재사용한다.

EC는 OURS/OURS-noGRAPH만 설치시+36tick 주기로 검사한다. 다음9Hz tick에 거절을 적용한다. 설치거절은 기존 경로·진행도·만료시각 유지. 주기거절은 같은경로에서 frozen stop_command로감속,새경로가EC통과해설치되어야재개한다. 회복·대체후보·0.1m/s 없음. 원SAFE의EC거절은Graph시도를억제하지 않으며Graph결과도설치전EC검사한다.

52-P 대비: 제동꼬리/정확swept/주기는같고 컨트롤러는공통Phase18 PP/CURV를전달하며사용자지시에따라대체후보/0.1/STOP_WAIT를제거한다. ENDPOINT·2s이후실제stop_command로정지까지검사한다.

주비교2개: OURS−RTC checkpoint평균짝차 seed클러스터bootstrap20,000회(seed20261030),양측95% CI와중심화bootstrap p; OURS대noEC 안전실패(충돌OR벽침범) exact McNemar양측p. Holm α=.05. 주비교는완료seed블록의기술PASS관측짝만,결측대체없음. 중간report는「중간 결과, 판정 보류」로명시한다.

LC/OURS/seed95/30s smoke1회만결과제외. 첫main RUN_DONE을1회확인하며기술실패면중지·배관수정1회재실행만허용한다. root/global lock,30GB디스크하한,run후cache정리. report는systemPython으로자동commit/push한다.

진행확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_j1.campaign --status`

로그: `../artifacts/isaac6/j1_01.log`

실행/재개 명령:

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && setsid nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j1.campaign > ../artifacts/isaac6/j1_01.log 2>&1 < /dev/null &`

## 실행 전 smoke 기록

GPU 미노출 샌드박스의 smoke_01은 NoMaD worker 시작 단계에서 종료되어 Isaac·주행은0회였다. 로그와 실패 기록은 보존했다. GPU 접근 환경의 smoke_02(LC/OURS/seed95/30s)는 기술 audit PASS이며 본 결과에서 제외한다. 실제 smoke 주행1회, main0회. protocol hash는 변경하지 않았다.

| audit | Graph 시도 | Graph 적용 | EC 검사 | protocol SHA256 |
|---|---:|---:|---:|---|
| PASS | 28 | 21 | 83 | 2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586 |
