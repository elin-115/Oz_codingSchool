# 🧪 Day10 통합 테스트 (FastAPI ↔ Redis ↔ AI 워커)

- 대상: AI 폐렴 예측 `POST /api/v1/medical-records/{record_id}/predict`
- 목표: 과제 완료 조건 확인
  - fastapi와 ai-worker 도커 서비스가 분리되어 있음
  - 요청 → Redis 큐에 작업 삽입 → 워커가 예측 → Pub/Sub으로 결과 전달 → FastAPI가 DB 저장·응답
- 기준 문서: [Day10 AI 워커 분리 설계](day10_AI워커_분리_설계.md)
- 테스트 날짜:
- 참여: 김지연, 김도엽, 박유정

## 0. 준비

```bash
git switch develop && git pull origin develop
docker compose down && docker volume rm oz_codingschool_venv_volume   # 처음 한 번만 ("no such volume"이면 이미 없는 것)
docker compose up --build -d --scale ai-worker=2
docker compose ps
```

- [ ] `.env`에 `REDIS_HOST`, `REDIS_PORT` 있음
- [ ] `worker/models/`에 fold1 모델 파일 3개 있음
- [ ] 로그 보기 (터미널을 따로 열어 두기)
  ```bash
  docker compose logs -f ai-worker
  ```
  ```bash
  docker compose exec redis redis-cli MONITOR
  ```
  `MONITOR`는 Redis에 들어오는 명령(`LPUSH`, `BRPOP`, `PUBLISH`, `SUBSCRIBE`)을 실시간으로 보여 줌 → 흐름 캡처용

## 1. 서비스 분리 확인

```bash
docker compose ps
```

| 확인 | 기대 결과 | 결과 |
|---|---|---|
| 컨테이너 | fastapi, ai-worker ×2, redis, mysql | |
| fastapi | `healthy` | |
| ai-worker 로그 | `[AI 모델] ... 불러오기 완료 (3개)`, `[AI 워커] 시작!` (2개 모두) | |
| fastapi 로그 | AI 모델 불러오기 메시지 **없음** (모델은 워커만 로딩) | |

📸 캡처: `docker compose ps`, 워커 시작 로그

## 2. 기본 흐름 (화면)

로그인 → 환자 등록 → 진료기록 등록(X-Ray 업로드) → **AI 예측**

| # | 시나리오 | 기대 결과 | 결과 |
|---|---|---|---|
| 2-1 | 새 진료기록 예측 | `201`, 폐렴 여부·신뢰도·히트맵 표시 | |
| 2-2 | 워커 로그 | `완료 task_id=... status=success` (워커 1개만) | |
| 2-3 | Redis MONITOR | `SUBSCRIBE` → `LPUSH ai:predict:queue` → `BRPOP` → `PUBLISH ai:predict:result:{task_id}` 순서 | |
| 2-4 | 결과 목록 | `GET /analyses`에 방금 결과 | |
| 2-5 | DB | `ai_analysis_results`에 1행, `ai_model = ensemble_3models_fold1_v1` | |
| 2-6 | 히트맵 파일 | `media/heatmap/`에 새 파일, 화면에 표시 | |

📸 캡처: 예측 결과 화면, 워커 로그, MONITOR 흐름

## 3. 기존 결과 재사용 (필수 조건)

| # | 시나리오 | 기대 결과 | 결과 |
|---|---|---|---|
| 3-1 | 같은 진료기록을 다시 예측 | `200`, 같은 결과 id | |
| 3-2 | 워커 로그 | 새 `완료` 로그 **없음** (큐에 안 넣음) | |
| 3-3 | DB | 행 개수 그대로 | |

## 4. 다중 워커

| # | 시나리오 | 기대 결과 | 결과 |
|---|---|---|---|
| 4-1 | 진료기록 3~4개를 연달아 예측 | 모두 `201` | |
| 4-2 | 워커 로그 | `ai-worker-1`, `ai-worker-2`가 작업을 나눠 처리, 같은 task_id가 두 번 나오지 않음 | |

📸 캡처: 두 워커 로그

## 5. 동시 요청 (따닥 방지 락)

| # | 시나리오 | 기대 결과 | 결과 |
|---|---|---|---|
| 5-1 | 새 진료기록에서 예측 버튼 빠르게 두 번 (또는 Swagger 두 탭에서 동시에) | 첫 번째 `201`, 두 번째 `409 이미 AI 예측이 진행 중입니다.` | |
| 5-2 | DB | 결과 1행만 | |
| 5-3 | 예측 끝난 뒤 다시 예측 | `200` 기존 결과 (409 아님 → 락이 풀림) | |

## 6. 에러 코드

| # | 시나리오 | 방법 | 기대 결과 | 결과 |
|---|---|---|---|---|
| 6-1 | X-Ray 파일 없음 | 진료기록의 `media/xray/` 파일을 잠깐 다른 곳으로 옮기고 예측 | `404` (FastAPI 사전 확인) | |
| 6-2 | 모델 준비 안 됨 | 모델 파일을 잠깐 옮기고 `docker compose restart ai-worker` 후 예측 | `503 AI 모델이 준비되지 않았습니다.` | |
| 6-3 | 워커 없음 (타임아웃) | `docker compose stop ai-worker` 후 예측 | 60초 뒤 `504 AI 예측 시간이 초과되었습니다.` | |
| 6-4 | 6-3 직후 다시 예측 | 워커를 켜고 바로 예측 | `409`가 아니라 정상 처리 (락 해제 확인) | |

> ⚠️ 6-3 동안 큐에 남은 작업은 워커를 다시 켜면 처리됨 (결과는 받을 사람이 없어 사라지고, 히트맵 파일만 남을 수 있음)

- 테스트 후 옮긴 파일 원래대로, `docker compose up -d --scale ai-worker=2`

## 7. 자동 테스트

```bash
uv run pytest -q
```

| 확인 | 기대 결과 | 결과 |
|---|---|---|
| 전체 테스트 | 모두 통과 | |

## 📋 결과 요약

| 항목 | 결과 | 확인한 사람 |
|---|---|---|
| 1. 서비스 분리 | | |
| 2. 기본 흐름 | | |
| 3. 기존 결과 재사용 | | |
| 4. 다중 워커 | | |
| 5. 동시 요청 | | |
| 6. 에러 코드 | | |
| 7. 자동 테스트 | | |

## 🔍 발견한 문제

| 문제 | 원인 | 조치 |
|---|---|---|
| | | |
