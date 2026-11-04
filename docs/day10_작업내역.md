# 📝 Day10 작업 내역

- 날짜: 2026-11-04
- PR: #75·#76 (9일차 설계 문서), #77 (Redis 서비스 + AI 워커 약속·뼈대), #78 (워커 Dockerfile·ai-worker 서비스), 문서 PR
- 작업자: 김지연, 김도엽, 박유정, 이명석
- 파일별 담당: 9일차 설계·Redis·약속·의존성·Docker 김지연 / FastAPI Redis 연결·예측 서비스 김도엽 (진행 중) / 워커 박유정 (진행 중)

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 7 | 9일차 설계 문서·도식, `worker/task_contract.py`, `worker/Dockerfile`, 뼈대 3개(`app/core/redis_client.py`, `worker/redis_client.py`, `worker/main.py`), Day10 설계 문서 |
| ✏️ 수정한 것 | 7 | `docker-compose.yml`, `pyproject.toml`·`uv.lock`, `worker/model.py`, `app/core/config.py`, `.env.example`, `app/Dockerfile` |
| 📦 fastapi 이미지 | 1.91GB → 960MB | torch를 ai 그룹으로 분리 (라이브러리 약 1.5GB → 201MB) |

| PR | 내용 |
|---|---|
| #75 | 9일차 FastAPI·Redis Event-Driven Architecture 공부, Excalidraw 아키텍처 도식 |
| #76 | 9일차 문서에 "한눈에 보기 (지금 vs 바꾼 설계)" 추가 |
| #77 | 10일차 과제 1 Redis 서비스 + AI 워커 약속·의존성 분리·뼈대 |
| #78 | 10일차 과제 3-2·3-3 워커 Dockerfile, compose ai-worker, fastapi 이미지에서 torch 제외 |
| 문서 PR | Day10 작업내역, 9일차 설계에 실제 구현 차이 추가 |

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

## ✅ 확인한 것

| 확인 | 결과 |
|---|---|
| Redis | `Up (healthy)`, `PONG` |
| 의존성 | `uv lock`·`uv sync` OK, pytest 12개 통과 |
| fastapi 이미지 | redis ✅, torch·PIL 없음, 960MB |
| ai-worker 이미지 | torch 2.14.1+cpu, redis, task_contract import ✅, 1.28GB |
| `venv_volume` 제거 후 | fastapi 컨테이너에서 `import redis` ✅ |

## 💡 배운 것

- **Pub/Sub은 듣고 있지 않으면 메시지가 사라짐.** 그래서 FastAPI는 결과 채널을 먼저 구독하고 나서 큐에 작업을 넣어야 함
- **약속(이름·형식)을 먼저 정하면** FastAPI 쪽과 워커 쪽이 서로 기다리지 않고 동시에 작업할 수 있음
- **의존성 그룹**으로 이미지마다 필요한 라이브러리만 설치 → 무거운 torch는 워커에만
- **`uv run`은 실행 전에 자동으로 설치(sync)함.** 이미지 안에서는 `--no-sync`로 막아야 함
- **이름 있는 볼륨은 처음 내용을 계속 보관함.** 이미지를 새로 빌드해도 볼륨이 덮어쓰면 옛날 내용이 보임
- **설계와 구현이 달라질 수 있음.** 바뀐 점과 이유를 설계 문서에 남겨 두면 헷갈리지 않음

## ⏭️ 남은 작업

- [x] Redis 서비스 (과제 1)
- [x] 약속·의존성 분리·뼈대
- [x] 워커 Dockerfile, compose ai-worker, fastapi 이미지 torch 제외
- [ ] #78 머지 → 팀원 `docker compose down && docker volume rm oz_codingschool_venv_volume`
- [ ] FastAPI Redis 연결·예측 서비스 수정 (김도엽)
- [ ] 워커 BRPOP·예측·Publish (박유정)
- [ ] 통합 테스트 (`docker compose up --build`, 화면에서 AI 예측)
- [ ] (선택) 따닥 방지 락, 미완료 작업 복구
