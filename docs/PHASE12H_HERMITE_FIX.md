원인: index 25의 첫 switch(tick 136, prediction 0)에서 `join_endpoint_clamped`가 NumPy bool이어서 `events.jsonl` JSON 직렬화가 실패했다.
수정: 해당 메타데이터 값만 Python `bool(...)`로 변환한다. Hermite 정의·경로·PP/CURV 계산은 변경하지 않는다.
확인: `async_thread_failure.txt`의 TypeError를 저장 입력으로 재현했다. 기존 Phase 12 결과/raw는 보존하고 Phase 12-H를 별도 commit·시점·출력 경로로 실행한다.
