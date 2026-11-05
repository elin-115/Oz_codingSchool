# 🤖 Day10 AI 워커 분리 설계 (FastAPI ↔ Redis ↔ AI 워커 약속)

> 9일차 [동시성 문제 해결을 위한 아키텍처 설계](9일차_동시성문제_해결을위한_아키텍처설계.md)를 실제 코드로 옮기기 전에, FastAPI와 AI 워커가 주고받을 형식과 역할을 정함  
> 이 문서와 `worker/task_contract.py`를 기준으로 각자 작업함

## 0. 시작 전 준비 (팀원 모두)

```bash
git switch develop && git pull origin develop
uv sync                          # redis 라이브러리 새로 설치
docker compose up -d redis       # 로컬 Redis 실행
docker compose exec redis redis-cli ping   # PONG 나오면 준비 완료
```

- 로컬 `.env`에 아래 두 줄 추가 (`.env.example` 참고)
  ```
  REDIS_HOST=localhost
  REDIS_PORT=6379
  ```

## 1. 전체 흐름

```
① 브라우저 ── POST /predict ──▶ FastAPI
② FastAPI: 진료기록 확인 → 같은 이미지·모델 결과가 DB에 있으면 바로 200 + 기존 결과 (큐에 안 넣음)
③ FastAPI: 결과 채널 SUBSCRIBE  ← 반드시 큐에 넣기 "전에" 구독
④ FastAPI ── LPUSH 작업 ──▶ Redis 큐 (ai:predict:queue)
⑤ AI 워커 ── BRPOP ──▶ 작업 하나 꺼냄 (워커가 여러 개여도 하나만 가져감)
⑥ AI 워커: X-Ray 읽기 → 예측 → 히트맵 이미지 저장 (공유 media 폴더)
⑦ AI 워커 ── PUBLISH 결과 ──▶ Redis 채널 (ai:predict:result:{task_id})
⑧ FastAPI: 결과 받음 → MySQL 저장 → 201 + 결과 응답 (60초 안에 안 오면 504)
```

| 9일차 설계와 달라진 점 | 이유 |
|---|---|
| DB 저장을 워커가 아니라 **FastAPI**가 함 | 과제 조건: "결과를 pub/sub으로 전달해 FastAPI에서 DB에 저장" |
| 결과를 상태 조회(폴링) 대신 **Pub/Sub 구독**으로 받음 | 과제 조건. 응답 형식(201/200)이 지금 API와 같아서 프론트 수정 없음 |

## 2. 약속 (`worker/task_contract.py`)

| 이름 | 값 | 쓰는 곳 |
|---|---|---|
| `QUEUE_NAME` | `ai:predict:queue` | FastAPI `LPUSH`, 워커 `BRPOP` |
| `result_channel(task_id)` | `ai:predict:result:{task_id}` | 워커 `PUBLISH`, FastAPI `SUBSCRIBE` |
| `MODEL_NAME` | `ensemble_3models_fold1_v1` | 기존 결과 확인, DB `ai_model` 값 |
| `RESULT_TIMEOUT` | `60` (초) | FastAPI가 결과를 기다리는 최대 시간 |

- 이 파일은 torch를 import하지 않음 → torch가 없는 FastAPI 이미지에서도 import 가능
- 이름을 바꿀 땐 이 파일 하나만 고침

### 작업 메시지 (FastAPI → 워커)

```json
{ "task_id": "uuid 문자열", "record_id": 12, "image_url": "/media/xray/abc.png" }
```

### 결과 메시지 (워커 → FastAPI)

```json
{ "task_id": "...", "status": "success", "is_pneumonia": true, "confidence": 87.5,
  "heatmap_url": "/media/heatmap/def.png", "ai_model": "ensemble_3models_fold1_v1" }
```

```json
{ "task_id": "...", "status": "error", "error_code": "IMAGE_NOT_FOUND", "error": "X-Ray 이미지 파일을 찾을 수 없습니다." }
```

#### 에러 코드 (`error_code`)

FastAPI는 에러 문장(`error`)이 아니라 **`error_code`로 응답 상태 코드를 정함**. 문장은 화면에 보여 줄 메시지로만 사용

| 상수 (`task_contract.py`) | 값 | 상황 | FastAPI 응답 | 메시지 예 |
|---|---|---|---|---|
| `ERROR_IMAGE_NOT_FOUND` | `IMAGE_NOT_FOUND` | X-Ray 파일이 없음 | **404** | X-Ray 이미지 파일을 찾을 수 없습니다. |
| `ERROR_MODEL_NOT_READY` | `MODEL_NOT_READY` | 워커에 모델 파일이 없거나 로딩 실패 | **503** | AI 모델이 준비되지 않았습니다. |
| `ERROR_PREDICT_FAILED` | `PREDICT_FAILED` | 그 밖의 예측 중 오류 | **500** | AI 예측 처리 중 오류가 발생했습니다. |
| (결과 없음) | - | `RESULT_TIMEOUT`초 안에 결과가 안 옴 | **504** | AI 예측 시간이 초과되었습니다. |

- 모르는 `error_code`가 오거나 없으면 500으로 처리
- 404·503은 예전 동기 API와 같은 상태 코드 (프론트 처리 그대로)

- `confidence`는 지금 DB와 같은 **0~100 (%)**
- `heatmap_url`은 DB에 그대로 저장할 주소 형식 (`/media/heatmap/...`)

## 3. 규칙

| 규칙 | 내용 |
|---|---|
| 구독 먼저, 큐는 나중에 | 큐에 먼저 넣으면 워커가 빨리 끝냈을 때 결과 메시지를 놓침 (Pub/Sub은 듣고 있지 않으면 사라짐) |
| 기존 결과 재사용 | `record_id + MODEL_NAME`으로 DB 확인 → 있으면 큐에 넣지 않고 200 |
| 타임아웃 | `RESULT_TIMEOUT`초 안에 결과가 없으면 504 "AI 예측 시간이 초과되었습니다." |
| 워커 실패 | `status: "error"`면 `error_code`로 404·503·500 응답 (2장 에러 코드 표) |
| 히트맵 | 워커가 만들어 `media/heatmap/`에 저장, 주소만 보냄. media 폴더는 FastAPI·워커가 볼륨으로 공유 |
| DB 저장 실패 | 지금처럼 rollback + 히트맵 파일 삭제 |
| 모델 로딩 | FastAPI `lifespan`에서 `load_model()` 제거 → 워커가 켜질 때 불러옴 |
| 워커는 죽지 않기 | 작업 하나가 실패해도 error 결과를 보내고 다음 작업으로 넘어감 |

## 4. 의존성 그룹 (`pyproject.toml`)

| 그룹 | 패키지 | 설치하는 곳 |
|---|---|---|
| 공통 `dependencies` | `pydantic-settings`, `redis` | 둘 다 |
| `app` | fastapi, sqlalchemy, asyncmy, alembic, pwdlib, pyjwt, cryptography, uuid6 | fastapi 이미지 (`uv sync --no-default-groups --group app`) |
| `ai` | torch, torchvision, pillow | ai-worker 이미지 (`uv sync --no-default-groups --group ai`) |
| `dev` | pytest, pytest-asyncio | 로컬 |

- 로컬에서는 `uv sync` 한 번이면 전부 설치됨 (`default-groups`)
- ⚠️ `app/` 코드에서 `torch`, `PIL`, `worker.model`을 import하면 fastapi 이미지에서 에러남. 히트맵 저장 함수(`save_heatmap_image`)는 워커 쪽으로 옮김

## 5. 분담

| 담당 | 파일 | 할 일 |
|---|---|---|
| 김지연 | `docker-compose.yml`, `pyproject.toml`, `worker/task_contract.py`, 이 문서 | Redis 서비스, 약속, 의존성 분리, 뼈대 ✅ |
| **김도엽** | `app/core/redis_client.py` | Redis 비동기 클라이언트 |
| | `app/services/ai_analyses.py` | 기존 결과 확인 → 구독 → 작업 LPUSH → 결과 대기(타임아웃) → DB 저장 |
| | `app/main.py` | `lifespan`의 `load_model()` 제거 |
| **박유정** | `worker/redis_client.py` | Redis 동기 클라이언트 |
| | `worker/main.py` | 모델 로딩, BRPOP 루프, 예측·히트맵 저장, 결과 PUBLISH |
| 김지연 | `worker/Dockerfile`, `app/Dockerfile`, `docker-compose.yml` | 워커 이미지, ai-worker 서비스, fastapi 이미지에서 torch 제외, media 공유 |
| 먼저 끝난 사람 | (선택) | 따닥 방지 락 (`SET NX EX`), 미완료 작업 복구 (`BLMOVE`) |

- 뼈대 파일에 `# ===== [이름] =====`과 `TODO`로 할 일을 적어 둠
- 작업 브랜치는 develop에서, PR은 develop으로

## 6. (선택) 따닥 방지 락 - `app/core/predict_lock.py`

같은 진료기록 예측을 동시에 여러 번 요청하면(버튼 "따닥") **첫 번째만 진행**하고 나머지는 막음

| 함수 | 하는 일 |
|---|---|
| `acquire_predict_lock(record_id)` | 락 잡기. 성공 `True`, 이미 예측 중이면 `False` (Redis `SET NX EX`) |
| `release_predict_lock(record_id)` | 락 풀기 (Redis `DEL`) |

- 락 키: `ai:predict:lock:{record_id}:{MODEL_NAME}`
- 자동 해제: `LOCK_EXPIRE = RESULT_TIMEOUT + 10` (70초). 서버가 죽어 release를 못 해도 저절로 풀림

### 서비스에서 쓰는 위치 (김도엽)

```python
from app.core.predict_lock import acquire_predict_lock, release_predict_lock

# 2. 기존 결과 확인 → 있으면 바로 200 (락 필요 없음)
# 3~4. X-Ray 이미지 확인

# 락 잡기: 이미 같은 예측이 진행 중이면 409
if not await acquire_predict_lock(record_id):
    raise HTTPException(status_code=409, detail="이미 AI 예측이 진행 중입니다.")

try:
    # 5~12. 구독 → LPUSH → 결과 대기 → DB 저장 (지금 코드 그대로)
    ...
finally:
    await release_predict_lock(record_id)   # 성공·실패·타임아웃 모두 락 해제
```

- 기존 결과 확인 **다음**에 잡음 → 첫 번째 예측이 끝난 뒤 다시 누르면 락 없이 기존 결과(200)를 돌려줌
- `finally`에서 풀어야 에러가 나도 락이 남지 않음

### 확인 결과 (로컬 Redis)

| 테스트 | 결과 |
|---|---|
| 같은 진료기록으로 5번 동시 요청 | `[True, False, False, False, False]` → 1개만 통과 |
| 락 남은 시간 | 70초 |
| 진행 중 재요청 / 해제 후 요청 | `False` / `True` |
| 해제 후 키 | 남지 않음 |

## 7. 각자 테스트하는 방법

| 담당 | 혼자 테스트 |
|---|---|
| 워커 (유정) | `uv run python -m worker.main`으로 워커 실행 → 다른 터미널에서 `redis-cli`로 작업 넣고 결과 구독<br>`docker compose exec redis redis-cli SUBSCRIBE ai:predict:result:test1`<br>`docker compose exec redis redis-cli LPUSH ai:predict:queue '{"task_id":"test1","record_id":1,"image_url":"/media/xray/파일명.png"}'` |
| FastAPI (도엽) | 서버 실행 후 예측 요청 → `redis-cli LRANGE ai:predict:queue 0 -1`로 작업이 들어갔는지 확인<br>워커 대신 `redis-cli PUBLISH ai:predict:result:{task_id} '{...성공 JSON...}'`로 결과를 보내 저장·응답 확인 |
| 통합 | `docker compose up --build` → 화면에서 AI 예측 |
