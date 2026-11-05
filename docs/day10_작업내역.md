# 📝 Day10 작업 내역

- 날짜: 2026-11-04 ~ 2026-11-05
- PR: #75·#76 (9일차 설계 문서), #77 (Redis 서비스 + AI 워커 약속·뼈대), #78 (워커 Dockerfile·ai-worker 서비스), #79 (작업내역), #80 (FastAPI 연동), #81 (에러 코드), #82 (따닥 방지 락), #83 (AI 워커), #84 (정리), #85 (워커 자동 재시작), #86 (미완료 작업 복구), #87 (AWS 배포 QA), #88 (통합 테스트)
- 작업자: 김지연, 김도엽, 박유정, 이명석
- 파일별 담당: 9일차 설계·Redis·약속·의존성·Docker·에러 코드·락·재시작·복구 김지연 / FastAPI Redis 연결·예측 서비스 김도엽 / 워커 박유정 / 통합 테스트 4명

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 9 | 9일차 설계 문서·도식, `worker/task_contract.py`, `worker/Dockerfile`, 뼈대 3개(`app/core/redis_client.py`, `worker/redis_client.py`, `worker/main.py`), Day10 설계 문서, `app/core/predict_lock.py`, 통합 테스트 문서 |
| ✏️ 수정한 것 | 12 | `docker-compose.yml`, `pyproject.toml`·`uv.lock`, `worker/model.py`, `app/core/config.py`, `.env.example`, `app/Dockerfile`, `app/services/ai_analyses.py`, `app/main.py`·`app/core/files.py`, `tests/test_ai_analyses.py`, `worker/main.py`·`worker/redis_client.py`, `worker/task_contract.py`, AWS 07 문서 |
| 🧪 통합 테스트 | 4명 | 8개 항목 전부 통과, 모든 항목을 2명 이상이 확인 |
| 📦 fastapi 이미지 | 1.91GB → 960MB | torch를 ai 그룹으로 분리 (라이브러리 약 1.5GB → 201MB) |

| PR | 내용 |
|---|---|
| #75 | 9일차 FastAPI·Redis Event-Driven Architecture 공부, Excalidraw 아키텍처 도식 |
| #76 | 9일차 문서에 "한눈에 보기 (지금 vs 바꾼 설계)" 추가 |
| #77 | 10일차 과제 1 Redis 서비스 + AI 워커 약속·의존성 분리·뼈대 |
| #78 | 10일차 과제 3-2·3-3 워커 Dockerfile, compose ai-worker, fastapi 이미지에서 torch 제외 |
| #79 | Day10 작업내역, 9일차 설계에 실제 구현 차이 추가 |
| #80 | 김도엽: FastAPI Redis 연결, 예측 서비스를 큐 + Pub/Sub 방식으로 변경, 테스트 수정 |
| #81 | 워커 실패 결과에 `error_code` 추가 (404/503/500 매핑) |
| #82 | 같은 진료기록 동시 예측을 막는 Redis 락 (409) |
| #83 | 박유정: AI 워커 Redis 연결, 큐 루프, 예측·히트맵 저장, 결과 PUBLISH |
| #84 | 공백·중복 주석·미사용 상수 정리 |
| #85 | `ai-worker`에 `restart: unless-stopped` |
| #86 | 미완료 작업 복구 (BRPOP → BLMOVE + 워커별 작업대 + EXPIRE) |
| #87 | AWS 배포 서버 기능 테스트 결과 (`docs/aws/07`) |
| #88 | Day10 통합 테스트 결과 (4명, 캡처 17장) |

## 🆕 새로 만든 것

### `docs/9일차_동시성문제_해결을위한_아키텍처설계.md` (#75, #76)

- **왜**: 9일차 과제 1·2. 지금 AI 예측 구조의 동시성 문제를 찾고 EDA로 해결하는 구조 설계
- **어떻게**
  - 지금 `predict_record()`에서 문제 5개 찾음: 추론이 API를 붙잡음, "기존 결과 확인 → 저장" 사이 경쟁 상태로 **중복 저장**(유니크 제약 없음), 동시 추론 폭주, 긴 HTTP 연결, API와 모델이 한 몸
  - EDA 개념, Redis 자료구조와 큐 원리(`LPUSH`/`BRPOP`), 202 + 상태 조회 패턴, 분산 락·멱등성 정리
  - Excalidraw로 FastAPI ↔ Redis ↔ AI 워커 도식 (`docs/images/day09/`, 원본 `.excalidraw` 포함)
  - 처음 읽는 사람을 위해 맨 앞에 햄버거 가게 비유 "한눈에 보기" 추가 (#76)

### `worker/task_contract.py` (#77)

- **왜**: FastAPI와 워커가 같은 이름·형식을 쓰도록 약속을 한 파일에 모음. 이름을 바꿀 땐 이 파일 하나만 고침
- **어떻게**: torch를 import하지 않아서 torch가 없는 fastapi 이미지에서도 import 가능

```python
QUEUE_NAME = "ai:predict:queue"              # 작업 대기열 (FastAPI LPUSH, 워커 BRPOP)
MODEL_NAME = "ensemble_3models_fold1_v1"     # worker/model.py에서 옮겨옴
RESULT_TIMEOUT = 60                          # FastAPI가 결과를 기다리는 최대 시간(초)

def result_channel(task_id: str) -> str:     # 작업마다 자기 결과만 받는 Pub/Sub 채널
    return f"ai:predict:result:{task_id}"
```

- 처음엔 `f"ai:predict:result:task_id"`로 써서 모든 작업이 같은 채널이 됨 → f-string 변수는 `{task_id}`로 감싸야 함

### 뼈대 파일 3개 (#77)

| 파일 | 담당 | 할 일 (TODO) |
|---|---|---|
| `app/core/redis_client.py` | 김도엽 | `redis.asyncio` 비동기 클라이언트 |
| `worker/redis_client.py` | 박유정 | `redis` 동기 클라이언트 (환경 변수 `REDIS_HOST`, `REDIS_PORT`) |
| `worker/main.py` | 박유정 | 모델 로딩, `BRPOP` 루프, 예측·히트맵 저장, 결과 `PUBLISH` |

- 실제 코드는 담당자가 작성. 뼈대에는 `# ===== [이름] =====`과 TODO만 적음

### `docs/day10_AI워커_분리_설계.md` (#77)

- **왜**: 팀원이 같은 기준으로 바로 작업할 수 있게
- **어떻게**: 시작 준비, 전체 흐름 ①~⑧, 작업·결과 JSON 형식, 규칙(구독 먼저 → 큐 나중, 60초 타임아웃, 히트맵은 워커가 저장), 의존성 그룹, 분담, 각자 테스트 방법

### `worker/Dockerfile` (#78)

- **왜**: 과제 3-2. AI 워커를 fastapi와 별도 이미지로
- **어떻게**: `ai` 그룹만 설치, `worker/` 폴더만 복사

```dockerfile
FROM python:3.13-slim
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
# ai 그룹만
RUN uv sync --frozen --no-default-groups --group ai
# 워커는 worker 폴더만 있으면 됨 - app 코드 필요 없음
COPY worker ./worker
# worker/main.py 실행
CMD ["uv", "run", "--no-sync", "python", "-m", "worker.main"]
```

- **만난 문제**
  - `--group torch` → 그룹 이름은 패키지 이름이 아니라 `pyproject.toml`에 붙인 이름(`ai`)
  - 줄 끝 `# 주석` → Dockerfile은 줄 끝 주석 불가, 위 줄로 옮김
  - `worker.main:worker` → `python -m`은 모듈 이름만 받음 (`:` 형식은 uvicorn용)

### `app/core/predict_lock.py` (#82)

- **왜**: 같은 진료기록에서 예측 버튼을 빠르게 두 번 누르면 "기존 결과 확인 → 저장" 사이에 둘 다 통과해서 결과가 **중복 저장**될 수 있음 (9일차에서 찾은 문제)
- **어떻게**: Redis `SET NX`(키가 없을 때만 저장)는 원자적이라 동시에 와도 하나만 성공함

```python
LOCK_EXPIRE = RESULT_TIMEOUT + 10   # 서버가 죽어서 못 풀어도 70초 뒤 저절로 풀림

def _lock_key(record_id: int) -> str:
    return f"ai:predict:lock:{record_id}:{MODEL_NAME}"

async def acquire_predict_lock(record_id: int) -> bool:
    ok = await redis_client.set(_lock_key(record_id), "1", nx=True, ex=LOCK_EXPIRE)
    return bool(ok)

async def release_predict_lock(record_id: int) -> None:
    await redis_client.delete(_lock_key(record_id))
```

- 예측 서비스는 락을 못 잡으면 `409 이미 AI 예측이 진행 중입니다.`, 끝나면 `finally`에서 항상 해제함

### `docs/day10_통합테스트.md`, `docs/images/day10/` (#88)

- **왜**: 과제 완료 조건(서비스 분리, 큐 → 워커 → Pub/Sub → DB 저장)을 4명이 같은 기준으로 확인
- **어떻게**: 시나리오 8개(서비스 분리, 기본 흐름, 결과 재사용, 다중 워커, 따닥 방지, 에러 코드, 미완료 작업 복구, pytest) + 팀원별 결과 + 발견한 문제
  - 처음엔 #86 전 내용이라 MONITOR 기대 흐름을 `BRPOP` → `BLMOVE`·`EXPIRE`·`LREM`으로 고치고 7번 복구 시나리오를 추가함
  - 팀원마다 OS(macOS·Windows)와 방법이 달라서 결과를 섹션별로 나눠 적음

## ✏️ 수정한 것

### `docker-compose.yml` - redis 서비스 (#77, 과제 1)

```yaml
# 후 (추가)
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_volume:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
```

```yaml
# fastapi 서비스 - 전
    environment:
      DB_HOST: mysql
      DB_PORT: "3306"
    depends_on:
      mysql:
        condition: service_healthy

# fastapi 서비스 - 후
    environment:
      DB_HOST: mysql
      DB_PORT: "3306"
      REDIS_HOST: redis            # 컨테이너끼리는 서비스 이름으로 접속
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
```

- **만난 문제**: 서비스 이름 오타 `radis`, 포트를 `"redis: 6379"`로 써서 `invalid containerPort` → 포트는 `"내 컴퓨터:컨테이너"` 숫자 형식
- **결과**: `docker compose up -d redis` → `Up (healthy)`, `redis-cli ping` → `PONG`

### `pyproject.toml`, `uv.lock` - 의존성 분리 (#77, 과제 3-1)

```toml
# 전: 전부 한 곳
dependencies = [
    "alembic>=1.18.4",
    "asyncmy>=0.2.11",
    "cryptography>=46.0.6",
    "fastapi[standard]>=0.135.3",
    "pillow>=13.0.0",
    "pwdlib[argon2]>=0.3.1",
    "pydantic-settings>=2.13.1",
    "pyjwt>=2.15.1",
    "sqlalchemy[asyncio]>=2.0.49",
    "torch>=2.14.1,<2.15",
    "torchvision>=0.29.1,<0.30",
    "uuid6>=2025.0.1",
]
```

```toml
# 후: 공통 / app / ai
dependencies = [
    "pydantic-settings>=2.13.1",
    "redis>=5.0",                  # 새로 추가
]

[dependency-groups]
app = [                            # FastAPI 이미지
    "alembic>=1.18.4",
    "asyncmy>=0.2.11",
    "cryptography>=46.0.6",
    "fastapi[standard]>=0.135.3",
    "pwdlib[argon2]>=0.3.1",
    "pyjwt>=2.15.1",
    "sqlalchemy[asyncio]>=2.0.49",
    "uuid6>=2025.0.1",
]
ai = [                             # AI 워커 이미지
    "pillow>=13.0.0",
    "torch>=2.14.1,<2.15",
    "torchvision>=0.29.1,<0.30",
]

[tool.uv]
default-groups = ["app", "ai", "dev"]   # 로컬 `uv sync`는 전부 설치
```

- **왜**: fastapi 이미지에 torch(수 GB)가 들어가지 않게
- `pillow`는 히트맵 저장 함수에서만 써서 워커 쪽(`ai`)으로. 그 함수는 도엽님 PR에서 워커로 옮겨짐
- **결과**: `uv lock`·`uv sync` 후 pytest 12개 통과, `app` 그룹만 설치하면 torch 없음, `ai` 그룹은 torch CPU 전용

### `worker/model.py` (#77)

```python
# 전
MODEL_NAME = "ensemble_3models_fold1_v1"

# 후
from worker.task_contract import MODEL_NAME
```

- 모델 이름 원본을 약속 파일 한 곳에만 둬서, 한쪽만 바꾸는 실수 방지

### `app/core/config.py`, `.env.example` (#77)

```python
# 후 (추가)
    # Redis 설정 (AI 예측 작업 대기열, 결과 Pub/Sub). 도커에서는 compose가 REDIS_HOST=redis로 덮어씀
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
```

```
# .env.example 후 (추가)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### `app/Dockerfile` (#78)

```dockerfile
# 전
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 후
RUN uv sync --frozen --no-default-groups --group app
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- `--no-sync`: `uv run`은 실행 전에 기본 그룹(app·ai·dev)을 자동 설치하려고 해서, 그대로 두면 컨테이너가 켜질 때 torch를 다시 받음

### `docker-compose.yml` - ai-worker 서비스, venv_volume 제거 (#78)

```yaml
# 후 (추가)
  ai-worker:
    build:
      context: .
      dockerfile: worker/Dockerfile
    environment:
      REDIS_HOST: redis
      PYTHONUNBUFFERED: "1"           # print가 바로 docker logs에 보이게
    volumes:
      - ./worker:/app/worker          # 코드 수정 바로 반영 + 모델 파일(worker/models)
      - ./media:/app/media            # fastapi와 같은 폴더 공유 (X-Ray 읽기, 히트맵 저장)
    depends_on:
      redis:
        condition: service_healthy
```

```yaml
# fastapi - 전
    command: ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev uvicorn ... --reload"]
    volumes:
      ...
      - venv_volume:/app/.venv

# fastapi - 후
    command: ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn ... --reload"]
    volumes:
      ...                              # venv_volume 줄 삭제 (맨 아래 volumes 목록에서도 삭제)
```

- **만난 문제**
  - `ai-worker:`를 4칸 들여써서 redis 서비스 안으로 들어감 → `mapping key "volumes" already defined` → 2칸으로
  - 새 이미지엔 redis가 있는데 컨테이너에선 `No module named 'redis'`, 옛날 torch도 그대로 → **`venv_volume`이 처음 만들 때의 `.venv`를 계속 보관해서 새 이미지를 덮어씀**. 코드는 폴더별로만 연결해서 원래 필요 없던 볼륨이라 제거
- 다중 워커: `docker compose up --scale ai-worker=2`

### `docs/9일차_동시성문제_해결을위한_아키텍처설계.md` - 실제 구현 차이 (문서 PR)

- 5장 끝에 "10일차 실제 구현에서 바뀐 점" 표 추가: DB 저장은 FastAPI, 결과는 Pub/Sub으로 받음, 응답은 201/200 유지, 락은 선택 과제

### `app/services/ai_analyses.py` - 예측을 워커에 맡김 (#80 김도엽, #82, #84)

- **왜**: 과제 2-1. FastAPI가 모델을 직접 돌리지 않고 Redis 큐로 워커에 맡김
- **어떻게**

```python
# 전: FastAPI 안에서 직접 예측
prediction = await run_in_threadpool(ai_model.predict, image_path)
heatmap = await run_in_threadpool(ai_model.make_heatmap, image_path)
heatmap_url = await run_in_threadpool(save_heatmap_image, heatmap)
```

```python
# 후: 락 → 구독 먼저 → 큐에 넣기 → 결과 기다리기
if not await acquire_predict_lock(record_id):          # #82
    raise HTTPException(status.HTTP_409_CONFLICT, "이미 AI 예측이 진행 중입니다.")

pubsub = redis_client.pubsub()
await pubsub.subscribe(result_channel(task_id))        # 결과를 놓치지 않게 먼저 구독
await redis_client.lpush(QUEUE_NAME, json.dumps(task)) # 그다음 큐에 작업 등록

# RESULT_TIMEOUT(60초) 동안 1초씩 결과 확인 → 없으면 504
# 워커 결과의 error_code로 응답 코드 결정 (#81)
error_status_by_code = {
    ERROR_IMAGE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ERROR_MODEL_NOT_READY: status.HTTP_503_SERVICE_UNAVAILABLE,
    ERROR_PREDICT_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
}
# finally: 구독 해제 + 락 해제, DB 저장 실패 시 워커가 만든 히트맵 파일 삭제
```

- 결과가 오면 `task_id`·`ai_model`·`is_pneumonia`·`heatmap_url` 형식을 검사하고, 이상하면 `502`
- 기존 결과 재사용(200), X-Ray 파일 사전 확인(404)은 큐에 넣기 전에 그대로 처리함
- #84: 락 아래 중복 주석 삭제, `# 10. Worker 오류 처리` 들여쓰기 9칸 → 8칸

### `app/main.py`, `app/core/files.py` - 모델·히트맵 코드 제거 (#80, #84)

- **왜**: fastapi 이미지엔 torch·PIL이 없음 (#78). 모델 로딩과 히트맵 저장은 이제 워커가 함

```python
# app/main.py 전: 서버가 켜질 때 모델 로딩
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield

app = FastAPI(lifespan=lifespan, ...)
```

```python
# 후: lifespan 삭제
app = FastAPI(...)
```

- `app/core/files.py`: `save_heatmap_image()`와 `from PIL import Image` 삭제 (#80), 안 쓰는 `HEATMAP_FOLDER` 상수 삭제 (#84)

### `tests/test_ai_analyses.py` (#80 김도엽)

- **왜**: 예측이 Redis를 거치게 바뀌어서 기존 테스트(모델 직접 호출)가 맞지 않음
- **어떻게**: Redis를 가짜 객체로 바꿔 워커 결과를 흉내 냄. 성공 201, 재사용 200, 에러 코드별 404/503/500, 타임아웃 504 테스트 → 전체 16개 통과

### `worker/main.py`, `worker/redis_client.py` - AI 워커 (#83 박유정, #86)

- **왜**: 과제 2-2. 큐에서 작업을 꺼내 예측하고 결과를 PUBLISH
- **어떻게 (#83)**: 켜질 때 `load_model()` 한 번 → 무한 반복(꺼내기 → `handle_task()` → `publish`)
  - 이미지 없음·모델 없음은 `error_code`를 담은 error 결과로 보냄
  - 그 밖의 예외도 잡아서 `PREDICT_FAILED`로 보냄 → **어떤 에러가 나도 워커는 죽지 않음**
  - 히트맵은 워커가 `media/heatmap/`에 저장하고 주소만 보냄 (fastapi와 `media` 폴더 공유)
  - `worker/redis_client.py`: `decode_responses=True`, `socket_timeout=None` (작업이 없을 때 무한 대기)
- **미완료 작업 복구 (#86)**: BRPOP은 꺼내는 순간 큐에서 지워서, 예측 중에 워커가 죽으면 작업이 사라짐

```python
# 전
_, raw_task = redis_client.brpop(QUEUE_NAME)
...
redis_client.publish(result_channel(task_id), json.dumps(result))
```

```python
# 후
worker_name = socket.gethostname()           # 컨테이너 이름, 재시작해도 그대로
processing = processing_queue(worker_name)   # 이 워커 전용 작업대

# 켜질 때: 지난번에 처리하다 죽은 작업을 큐로 되돌림
recovered = 0
while redis_client.lmove(processing, QUEUE_NAME, "LEFT", "RIGHT"):
    recovered += 1

# 꺼내면서 작업대로 옮김 (원자적이라 중간에 사라지지 않음)
raw_task = redis_client.blmove(QUEUE_NAME, processing, 0, src="RIGHT", dest="LEFT")
redis_client.expire(processing, RESULT_TIMEOUT * 2)   # 버려진 작업대는 120초 뒤 자동 삭제
...
redis_client.publish(result_channel(task_id), json.dumps(result))
redis_client.lrem(processing, 1, raw_task)            # 결과를 보낸 뒤에만 작업대에서 삭제
```

- 처음 작성 때 실수: f-string 중괄호 누락(`processing:worker_name`), 변수 대신 글자 `"task_queue"`, `lmove` 인자 순서 반대, `blmove` 인자 하나만, import 목록의 쉼표를 마침표로 씀 → 리뷰하면서 고침
- `EXPIRE`를 `* 1`(60초)이 아니라 `* 2`(120초)로 한 이유: 작업이 큐에서 기다린 시간과 워커 재시작·모델 로딩 시간까지 넉넉히 기다리기 위함
- 한계: 컨테이너를 **새로 만들면** hostname이 바뀌어 옛 작업대는 복구하지 않고 120초 뒤 지워짐. 그 작업은 FastAPI가 이미 504로 응답을 끝낸 상태라 의도한 동작임

### `worker/task_contract.py` - 에러 코드, 작업대 이름 (#81, #86)

```python
# 후 (추가, #81)
ERROR_IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"   # → 404
ERROR_MODEL_NOT_READY = "MODEL_NOT_READY"   # → 503
ERROR_PREDICT_FAILED = "PREDICT_FAILED"     # → 500

# 후 (추가, #86)
def processing_queue(worker_name: str) -> str:
    return f"ai:predict:processing:{worker_name}"
```

- #81 이유: 에러 문장을 비교하면 문장이 조금만 바뀌어도 응답 코드가 틀어짐. 코드(약속된 값)로 비교하고 문장은 화면 메시지로만 씀

### `docker-compose.yml` - ai-worker 자동 재시작 (#85)

```yaml
# 후 (추가)
  ai-worker:
    restart: unless-stopped
```

- **왜**: Redis 연결이 끊기는 등으로 워커가 스스로 종료돼도 다시 켜지게
- 참고 (박유정): `docker compose kill`·`stop`은 **직접 끈 것**이라 자동 재시작되지 않음 → `docker compose start`로 켬

### `docs/aws/07_서버_실행_테스트.md`, `docs/aws/README.md` (#87)

- **왜**: AWS 배포 과제 8단계 "배포 주소에서 모든 기능 테스트" 마무리
- **어떻게**: 11/05 서버 상태(2일 무중단), 첫 계정 승인 방법, 브라우저 기능 테스트 표 + 캡처 8장. 배포 이미지는 Day10 이전 구조(fastapi + mysql + nginx)로 과제 가이드 구성과 같음을 명시. 팀원 QA는 진행하지 않기로 함

## ✅ 확인한 것

| 확인 | 결과 |
|---|---|
| Redis | `Up (healthy)`, `PONG` |
| 의존성 | `uv lock`·`uv sync` OK, pytest 12개 통과 |
| fastapi 이미지 | redis ✅, torch·PIL 없음, 960MB |
| ai-worker 이미지 | torch 2.14.1+cpu, redis, task_contract import ✅, 1.28GB |
| `venv_volume` 제거 후 | fastapi 컨테이너에서 `import redis` ✅ |
| pytest | 16 passed (#80 이후) |
| 통합 테스트 (#88) | 1~8번 전부 통과. 김지연·이명석은 전체, 박유정은 4·7번, 김도엽은 1·2·8번 |
| 미완료 작업 복구 (#86) | 화면에서 예측 중 워커 kill → 14초 뒤 start → `미완료 작업 1개 복구` → 60초 안에 끝나 사용자는 `201`로 결과를 받음 |
| AWS 배포 서버 (#87) | 회원·관리자·환자·진료기록·AI 예측 브라우저 테스트 통과 |

## 💡 배운 것

- **Pub/Sub은 듣고 있지 않으면 메시지가 사라짐.** 그래서 FastAPI는 결과 채널을 먼저 구독하고 나서 큐에 작업을 넣어야 함
- **약속(이름·형식)을 먼저 정하면** FastAPI 쪽과 워커 쪽이 서로 기다리지 않고 동시에 작업할 수 있음
- **의존성 그룹**으로 이미지마다 필요한 라이브러리만 설치 → 무거운 torch는 워커에만
- **`uv run`은 실행 전에 자동으로 설치(sync)함.** 이미지 안에서는 `--no-sync`로 막아야 함
- **이름 있는 볼륨은 처음 내용을 계속 보관함.** 이미지를 새로 빌드해도 볼륨이 덮어쓰면 옛날 내용이 보임
- **설계와 구현이 달라질 수 있음.** 바뀐 점과 이유를 설계 문서에 남겨 두면 헷갈리지 않음
- **BRPOP은 꺼내는 순간 지움.** 처리 중에 죽어도 안전하려면 BLMOVE로 "작업대"에 옮겨 두고, 다 끝난 뒤에 지워야 함
- **Redis 명령 하나는 원자적임.** `SET NX`(락), `BLMOVE`(꺼내며 옮기기) 모두 동시에 와도 하나만 성공함
- **에러는 문장이 아니라 코드로 주고받음.** 문장은 바뀔 수 있어서 응답 코드를 정하는 기준으로 쓰면 깨지기 쉬움
- **로그는 응답이 끝난 순서로 찍힘.** 동시 요청에서 409가 201보다 먼저 보인 건, 409는 바로 응답하고 201은 예측이 끝나야 응답하기 때문
- **문법 에러는 밑줄 위치보다 한 줄 위를 먼저 봄.** 쉼표 대신 마침표를 찍으면 다음 줄에 밑줄이 생김

## ⏭️ 남은 작업

- [x] Redis 서비스 (과제 1)
- [x] 약속·의존성 분리·뼈대
- [x] 워커 Dockerfile, compose ai-worker, fastapi 이미지 torch 제외
- [x] #78 머지 → 팀원 `docker compose down && docker volume rm oz_codingschool_venv_volume`
- [x] FastAPI Redis 연결·예측 서비스 수정 (#80 김도엽)
- [x] 워커 큐 루프·예측·Publish (#83 박유정)
- [x] 통합 테스트 (#88)
- [x] 따닥 방지 락 (#82), 미완료 작업 복구 (#86)
- [ ] develop → main 반영
- [ ] (개선) 503·504일 때 화면에 서버 메시지 표시, 504 뒤 남은 작업은 워커가 건너뛰기
- [ ] AWS 리소스 정리 (`docs/aws/08`)
