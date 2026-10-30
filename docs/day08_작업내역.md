# 📝 Day08 작업 내역

- 날짜: 2026-10-30
- PR: #61 (Dockerfile), #62 (torch CPU 전용), #63 (compose fastapi), #64 (.dockerignore) <!-- TODO: compose mysql, 문서 PR 추가 -->
- 파일별 담당: Dockerfile·torch CPU 전용·문서 김지연 / .dockerignore 박유정 / compose fastapi 이명석 / compose mysql 김도엽

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | <!-- TODO --> | `app/Dockerfile`, `.dockerignore`, 캡처 `docs/images/day08/`, 실행 화면 문서 `day08_도커_실행화면.md` |
| ✏️ 수정한 것 | <!-- TODO --> | `pyproject.toml`, `uv.lock` (torch CPU 전용), `docker-compose.yml` (fastapi 서비스) <!-- TODO: mysql, README --> |
| 📦 이미지 크기 | 12GB → 4.31GB → 1.91GB | torch CPU 전용(#62) → .dockerignore(#64) |

| PR | 내용 |
|---|---|
| #61 | `app/Dockerfile` 작성 + 과제 1 빌드·실행 캡처, Day07 작업내역 PR 표 담당 열 정리 |
| #62 | 리눅스(도커)에서 torch CPU 전용 설치로 이미지 크기 축소 |
| #63 | compose fastapi 서비스 + Dockerfile 실행 명령 `uvicorn`으로 (이명석) |
| #64 | 루트 `.dockerignore` (박유정) |
<!-- TODO: | #65 | compose mysql 서비스 + 연결 (김도엽) | -->

## 🆕 새로 만든 것

### `app/Dockerfile` (#61)

- **왜**: 과제 1. 어느 컴퓨터에서든 같은 환경으로 앱을 빌드·실행하기 위해
- **어떻게**
  - `python:3.13-slim` → `build-essential` → `uv` → `uv sync --frozen --no-dev` → 코드 복사 → `fastapi run --host 0.0.0.0`
  - 의존성 파일(`pyproject.toml`, `uv.lock`)을 코드보다 먼저 복사해서, 코드만 바뀌면 설치 단계는 캐시 사용
  - 빌드 context는 루트(`.`): `app/`, `worker/`, `static/`을 모두 써서
  - `.env`는 이미지에 넣지 않고 `docker run --env-file`로만 전달
- **만난 문제**: slim 이미지에 gcc가 없어서 `asyncmy` 컴파일 실패 → `build-essential` 추가

### `docs/images/day08/` - 과제 1 캡처

- 빌드 성공(`docker build`, `docker images`), 컨테이너 실행 로그(`docker run`, `docker ps`), 컨테이너로 띄운 `/docs`·홈 화면
- 로그·화면에 `.env` 비밀 값이 없는 것 확인

### `.dockerignore` (#64, 박유정)

- **왜**: 과제 1. 비밀 값·캐시·문서·로컬 가상환경이 이미지에 들어가지 않게
- **어떻게**
  - 빌드 context가 루트라서 `app/`이 아닌 루트에 둠
  - `.env`(`.env.example`만 남김), `.venv`·파이썬 캐시, 도구 캐시, 도커 설정, docs·README, IDE·git, tests, media, AI 모델 파일(`*.pt`) 제외
- **결과**: 이미지 4.31GB → 1.91GB, 켤 때 재설치 사라짐. 그동안 이미지 안에 `.env`가 들어 있던 것도 발견해 막음
- 모델 파일이 빠져서 `docker run`은 `-v worker/models`로 연결해서 실행

## ✏️ 수정한 것

### `pyproject.toml`, `uv.lock` - torch CPU 전용 (#62)

- **왜**: 리눅스에서 torch 기본 설치는 GPU(CUDA)용이라 nvidia 패키지만 수 GB. 맥 도커엔 GPU가 없어서 쓰지 않음
- **어떻게**
  - `[tool.uv.sources]`로 `sys_platform == 'linux'`일 때만 `https://download.pytorch.org/whl/cpu` 사용 → 맥 로컬은 그대로
  - 처음엔 도커 쪽만 torch 2.15.0으로 잡혀서 `torch<2.15`, `torchvision<0.30`으로 로컬(2.14.1)과 맞춤
- **결과**: 이미지 12GB → 4.31GB, 컨테이너 안 torch 2.14.1+cpu, AI 모델 3개 정상 로드, pytest 12개 통과
- 팀원은 머지 후 `uv sync` 한 번 실행

### `docker-compose.yml` - fastapi 서비스 (#63, 이명석)

- **왜**: 과제 2. 로컬 코드를 컨테이너에 연결해 수정하면 바로 반영되게
- **어떻게**
  - `./app:/app/app`, `./worker`, `./static`, `./media`를 폴더별로 마운트 → `app.main` 경로가 그대로 유지됨
  - `venv_volume:/app/.venv`로 로컬 `.venv`가 컨테이너 걸 덮어쓰지 않게 막음
  - `uvicorn ... --reload`, healthcheck는 curl 대신 python (slim 이미지엔 curl 없음)
  - Dockerfile `CMD`도 `uvicorn app.main:app`으로 맞춤
- 리뷰 때 `.dockerignore`가 같이 들어와서, 담당대로 유정님 PR로 분리 후 머지

<!-- TODO: compose mysql 서비스 + 연결 (도엽) -->

## 💡 배운 것

- **`RUN`은 빌드할 때, `CMD`는 컨테이너 켤 때 실행됨.** 설치는 `RUN`, 앱 실행은 `CMD`
- **slim 이미지는 가벼운 대신 컴파일 도구가 없음.** C 확장이 있는 라이브러리(`asyncmy`)는 리눅스 ARM용 완성 파일이 없으면 직접 컴파일해야 해서 gcc 필요
- **같은 `uv.lock`이라도 맥과 리눅스에서 받는 torch가 다름.** 리눅스 기본은 GPU용이라, 플랫폼별로 설치 저장소를 나눠야 이미지가 가벼워짐
- **`.dockerignore`가 없으면 로컬 `.venv`까지 이미지에 들어감.** 컨테이너 켤 때마다 가상환경을 지우고 재설치하는 원인이 됨
- **`.dockerignore`는 빌드할 때만 적용됨.** compose 볼륨 마운트로 로컬 폴더를 연결하면 로컬 `.venv`가 다시 컨테이너 안으로 들어올 수 있음

## ⏭️ 남은 작업

- [x] Dockerfile + 과제 1 캡처 (#61)
- [x] torch CPU 전용으로 이미지 축소 (#62)
- [x] .dockerignore (#64 유정)
- [x] compose fastapi 서비스 (#63 명석)
- [ ] compose mysql 서비스 + 연결 (도엽)
- [x] 과제 1 최종 캡처 교체
- [ ] 과제 2 캡처
- [ ] AI 결과 참고용 표시 (기준값 논의)
