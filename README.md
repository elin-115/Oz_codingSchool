# AI Health Web Assignment

흉부 X-Ray 이미지 기반 폐렴 판독 모델을 활용한 **폐렴 환자 관리 백오피스** 프로젝트입니다.

## 📚 문서

| Day | 문서 | 내용 |
|---|---|---|
| Day01 | [팀 규칙](docs/day01_team_rules.md) | 팀원, 팀 규칙, Git 협업 규칙, 커밋 컨벤션 |
| Day02 | [Git Branch 전략](docs/day02_git_branch_전략.md) | Git Flow와 GitHub Flow 비교, 우리 팀 브랜치 전략 |
| Day03 | [프로젝트 뜯어보기](docs/day03_프로젝트_뜯어보기.md) | 디렉터리·파일 역할, DB 연결, alembic, API 구현 흐름 |
| Day03 | [DB 마이그레이션](docs/day03_db_migration.md) | ERD 기반 모델 작성, 마이그레이션 결과, 트러블슈팅 |
| Day03 | [작업 내역](docs/day03_작업내역.md) | 새로 만든 파일, 수정한 파일, 이유와 방법 |

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
