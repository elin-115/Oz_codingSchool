# AI Health Web Assignment

흉부 X-Ray 이미지 기반 폐렴 판독 모델을 활용한 **폐렴 환자 관리 백오피스** 프로젝트입니다.


## Alembic Migration Guide

이 프로젝트는 데이터베이스 마이그레이션을 위해 Alembic을 사용합니다.

### 1. 마이그레이션 파일 생성 (자동 생성)
모델(`app/models/`)이 변경된 경우 다음 명령어를 실행하여 마이그레이션 파일을 생성합니다.
```bash
uv run alembic revision --autogenerate -m "변경 내용 설명"
```

### 2. 데이터베이스에 반영
생성된 마이그레이션을 데이터베이스에 적용하려면 다음 명령어를 실행합니다.
```bash
uv run alembic upgrade head
```

### 3. 이전 상태로 되돌리기 (Rollback)
마지막 마이그레이션을 취소하려면 다음 명령어를 실행합니다.
```bash
uv run alembic downgrade -1
```

## 🐳 도커로 실행하기

프로젝트 루트에 `.env`를 만든 뒤(`.env.example` 참고) 실행함.

```bash
docker compose up --build
```

- fastapi + mysql 컨테이너가 함께 뜸. mysql이 준비된 뒤 fastapi가 켜짐
- fastapi가 켜질 때 `alembic upgrade head`가 자동으로 실행돼 테이블이 최신 상태로 맞춰짐 (따로 실행할 필요 없음)
- 로컬 코드(`app/`, `alembic/`, `worker/`, `static/`)가 컨테이너에 연결돼 있어 수정하면 `--reload`로 바로 반영됨
- AI 모델 파일(`worker/models/*.pt`)은 Drive에서 받아 로컬 `worker/models/`에 두면 됨
- 접속: http://localhost:8000/docs

도커 이미지만 따로 빌드·실행할 때는 [Day08 도커 실행 화면](docs/day08_도커_실행화면.md) 참고.


## 📋 팀 작업판

Stage 1~6 단계별로 누가 무엇을 했는지, 세부 내역과 PR 번호를 한 페이지로 정리함.

👉 [3조 폐렴 백오피스 작업판](https://claude.ai/artifact/XAdRyoYF6AgLyK2kV5DR8Z)

## 📚 과제 문서

| Day | 날짜 | 문서 | 내용 |
|---|---|---|---|
| Day01 | 10/21 | [팀 규칙](docs/day01_team_rules.md) | 팀원, 팀 규칙, Git 협업 규칙, 커밋 컨벤션 |
| Day02 | 10/22 | [Git Branch 전략](docs/day02_git_branch_전략.md) | Git Flow와 GitHub Flow 비교, 우리 팀 브랜치 전략 |
| Day03 | 10/23 | [프로젝트 뜯어보기](docs/day03_프로젝트_뜯어보기.md) | 디렉터리·파일 역할, DB 연결, alembic, API 구현 흐름 |
| Day03 | 10/23 | [DB 마이그레이션](docs/day03_db_migration.md) | ERD 기반 모델 작성, 마이그레이션 결과, 트러블슈팅 |
| Day04 | 10/26 | [User API 설계](docs/day04_USER_API_설계.md) | 요구사항 기반 User API 10종 명세, 인증·권한 설계 |
| Day05 | 10/27 | [환자 관리 API 설계](docs/day05_환자관리_API_설계.md) | 환자 관리·진료기록 API 8종 명세, 의료진 권한, X-Ray 저장, 영구 삭제 |
| Day05 | 10/27 | [통합 테스트 시나리오](docs/day05_통합테스트_시나리오.md) | 프론트 화면 기준 환자·진료기록 테스트 6단계와 실행 결과 |
| Day06 | 10/28 | [AI 예측 API 설계](docs/day06_AI예측_API_설계.md) | AI 폐렴 예측·결과 목록 API 명세, 모델 선택, 히트맵 저장 |
| Day06 | 10/28 | [AI 예측 통합 테스트 시나리오](docs/day06_AI예측_통합테스트_시나리오.md) | 예측·재예측·오류 응답 자동 테스트와 화면 확인 결과 |
| Day06 | 10/29 | [통합 테스트 결과](docs/day06_통합테스트_결과.md) | 팀원별 화면·자동 테스트 결과, 공통 발견(시간 9시간·캐시), 개선 제안 6개 |
| Day07 | 10/29 | [앱 실행 화면](docs/day07_앱_실행화면.md) | `fastapi run`으로 실행한 API 20개의 프론트 화면 캡처와 동작 설명 |
| Day08 | 10/30 | [도커 실행 화면](docs/day08_도커_실행화면.md) | Dockerfile·.dockerignore 빌드·실행, docker compose(fastapi + mysql) 실행·--reload 확인 |

## 📝 작업 내역

매일 무엇을, 왜, 어떻게 만들고 바꿨는지 기록한다.

| Day | 날짜 | 문서 | 주요 작업 |
|---|---|---|---|
| Day01 | 10/21 | [작업 내역](docs/day01_작업내역.md) | 레포 설정, 브랜치 보호 규칙, 팀 규칙 문서화 |
| Day02 | 10/22 | [작업 내역](docs/day02_작업내역.md) | 회원 API 5종 협업, PR 흐름, 코드 리뷰 |
| Day03 | 10/23 | [작업 내역](docs/day03_작업내역.md) | DB 모델·마이그레이션, Soft Delete 전환, 팀원 DB 적용 |
| Day04 | 10/26~27 | [작업 내역](docs/day04_작업내역.md) | User API 10개, 코드 리뷰, 회원 목록 검색, 프론트 통합 테스트와 버그 수정, 조교님 확인 후 프론트 수정 |
| Day05 | 10/27 | [작업 내역](docs/day05_작업내역.md) | 환자·진료기록 API 8개, X-Ray 업로드·영구 삭제, 코드 리뷰, 프론트 통합 테스트와 개선 |
| Day06 | 10/28~29 | [작업 내역](docs/day06_작업내역.md) | AI 모델 결정(3종 앙상블), 폐렴 예측·결과 목록 API, Grad-CAM 히트맵, 코드 정리, 화면 통합 테스트 |
| Day07 | 10/29 | [작업 내역](docs/day07_작업내역.md) | 프론트 API 20개 연결 확인(`fastapi run`), API별 실행 화면 캡처, develop → main |
| Day08 | 10/30 | [작업 내역](docs/day08_작업내역.md) | Dockerfile, torch CPU 전용(12GB → 1.91GB), .dockerignore, docker compose(fastapi + mysql), alembic 자동 적용 |
