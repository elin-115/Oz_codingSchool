# 📝 Day03 작업 내역

- 날짜: 2026-10-23
- PR: #11 ~ #17
- 작업자: 김지연, 김도엽, 박유정, 이명석

## 요약

| 구분 | 파일 수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 10개 | Enum, 모델 5개, 마이그레이션, 문서 2개, 캡처 이미지 |
| ✏️ 수정한 것 | 3개 | TimestampMixin 버그 수정, 모델 등록, README |
| 🔄 추가 변경 | 2건 | 삭제 정책 Soft Delete로 변경, Swagger 프로젝트 정보 |
| 👥 팀원 기여 | 3명 | 모델 리뷰 분담, 로컬 DB 적용 캡처, 학습 정리 |

## PR 흐름

| PR | 내용 | 작성자 | 리뷰 |
|---|---|---|---|
| #11 | DB 모델 5종, 초기 마이그레이션, Day03 문서 초안 | 김지연 | 박유정, 김도엽, 이명석 |
| #12 | 삭제 정책을 Soft Delete로 변경 | 김지연 | 팀 논의 후 승인 |
| #13 | 학습 정리 (3. DB 연결 설정) | 김지연 | |
| #14 | Swagger에 프로젝트 소개와 팀원 정보 | 김지연 | |
| #15 | 학습 정리 (2. 파일별 역할) + DB 적용 캡처 | 김도엽 | 김지연 |
| #16 | 학습 정리 (4. 모델과 alembic) + DB 적용 캡처 | 이명석 | 김지연 |
| #17 | 학습 정리 (1. 디렉터리별 역할) + DB 적용 캡처 | 박유정 | 김지연 |

## 🆕 새로 만든 것

### `app/core/enums.py` - 선택지 목록(Enum)

- **무엇을**: 성별(`Gender`), 소속(`Department`), 권한(`UserRole`) 선택지 정의
- **왜**: ERD에서 `gender`, `department`, `role`이 Enum 타입이라 정해진 값만 저장되도록 선택지를 정의해야 한다. users와 patients가 함께 쓰므로 `core`에 공통으로 두었다.
- **어떻게**: 파이썬 `StrEnum`으로 작성. (ERD에 값 정의가 없어 템플릿 예시 값을 따름)
  - Gender: `M`(male), `F`(female)
  - Department: `DEV`(개발자), `MEDICAL`(의료진), `RESEARCH`(연구진)
  - UserRole: `PENDING`(승인 대기), `STAFF`, `ADMIN`

### `app/models/` - 모델 파일 5개

- **과제 조건**: "ERD를 참고해 모델을 작성하고, 테이블마다 파일을 따로 만들기"
- SQLAlchemy 2.0 방식(`Mapped`, `mapped_column`)으로 ERD의 컬럼 이름, 타입, 길이, NOT NULL, unique, FK를 옮김. 
- `created_at`, `updated_at`은 `TimestampMixin`을 상속해 반복을 줄였다.

| 파일 | 테이블 | 특징 |
|---|---|---|
| `users.py` | users | email, phone_number unique. role 기본값 `PENDING`, is_active 기본값 `True`. id를 bigint로 작성 (아래 참고) |
| `patients.py` | patients | 환자 삭제 시 진료 기록도 함께 삭제되도록 `cascade` 설정 |
| `medical_records.py` | medical_records | patient_id FK(`CASCADE`), chart_number unique. X-ray, AI 결과와 연결 |
| `xray_images.py` | xray_images | ERD에 `updated_at`이 없어 Mixin 대신 `created_at`만 작성. uploader_id가 NOT NULL이라 업로더가 있는 사용자는 삭제되지 않도록 `RESTRICT` |
| `ai_analysis_results.py` | ai_analysis_results | confidence(신뢰도 %)가 0-100만 저장되도록 `CheckConstraint` |

> **users.id를 bigint로 작성한 이유**  
> ERD에서 `users.id`는 integer인데, 이를 참조하는 `xray_images.uploader_id`는 bigint다.
> MySQL은 외래키 양쪽 타입이 같아야 연결되므로, ERD 그대로 만들면 마이그레이션이 실패한다.

### `alembic/versions/79aafc5cfec9_create_initial_models.py` - 마이그레이션 파일

- **과제 조건**: "alembic으로 마이그레이션 수행"
- **무엇을**: 테이블 5개를 만들고(`upgrade`) 지우는(`downgrade`) 명령을 담은 파일이다.  이 파일로 `alembic upgrade head`만 하면 같은 테이블이 생긴다.
- **어떻게**: `alembic revision --autogenerate`로 생성한 뒤, 자동 생성 결과의 문제 2개를 직접 고쳤다.
  1. **confidence 검증 누락**: autogenerate가 컬럼 안에 넣은 체크 제약을 감지하지 못해 `CheckConstraint`를 직접 추가했다.
  2. **downgrade 오류**: MySQL은 외래키가 사용 중인 인덱스를 먼저 지울 수 없는데, 자동 생성 코드는 "인덱스 삭제 → 테이블 삭제" 순서였다.  인덱스 삭제 줄을 빼고 테이블만 삭제하도록 바꿨다. (테이블을 지우면 인덱스도 함께 삭제된다.)

### `docs/day03_프로젝트_뜯어보기.md` - 과제 1 문서

- **왜**: 과제 1 제출물
- **어떻게**: 참고 자료와 템플릿 실제 코드를 보며 과제 항목 5개(디렉터리 역할, 파일 역할, DB 연결, 모델과 alembic, API 흐름)를 정리했다.

### `docs/day03_db_migration.md` - 과제 2 문서

- **왜**: 과제 2 제출물 ("이미지를 이 파일에 업로드")
- **어떻게**: 사용 환경, 모델과 관계, 마이그레이션 명령어, DBeaver 캡처, 동작 테스트 결과, 트러블슈팅 4개, 팀원 적용 방법 순서로 작성했다.

### `docs/images/day03_erd_dbeaver.png` - DBeaver 캡처

- 과제 2 조건 "DB 뷰어로 스키마 확인"의 증거
- DBeaver ER Diagram 화면을 캡처해 레포에 넣고 문서에서 불러왔다.

## ✏️ 수정한 것

### `app/core/db/models.py` - TimestampMixin 버그 수정

- **왜**: `default=datetime.now(UTC)`는 함수가 아니라 **함수를 실행한 결과(시각 값)** 를 넘긴다.  
서버가 켜질 때 한 번 정해진 시각이 이후 저장되는 모든 데이터의 `created_at`에 들어간다.
- **어떻게**: 함수를 넘기도록 `lambda`로 감쌌다. 이제 저장할 때마다 현재 시각을 구한다.  
`updated_at`의 `onupdate`도 같이 고쳤다.

```diff
- default=datetime.now(UTC)
+ default=lambda: datetime.now(UTC)
```

### `app/models/__init__.py` - 모델 등록

- **왜**: alembic(`env.py`)은 `from app import models`로만 모델을 불러온다.  
여기에 import하지 않은 모델은 alembic이 인식하지 못해 테이블이 생성되지 않는다. 원래는 빈 파일이었다.
- **어떻게**: 모델 5개를 import하고 `__all__`에 등록했다.

### `README.md` - 문서 목록

- 일별 작업내용 정리 문서 추가
- 기존표에 Day03 문서를 추가

## ✅ 확인한 것

| 항목 | 결과 |
|---|---|
| `alembic upgrade head` | 테이블 5개 + `alembic_version` 생성 |
| `alembic downgrade -1` → `upgrade head` | 정상 삭제 후 재생성 |
| 샘플 데이터 저장 | 성공, 기본값 정상 |
| confidence 150 저장 | 거부 |
| chart_number 중복 저장 | 거부 |
| 환자 삭제 | 진료 기록, X-ray, AI 결과 연쇄 삭제 (→ 아래에서 삭제 표시 방식으로 변경) |
| DBeaver | 테이블과 관계 확인 |

## 🔄 추가 변경: 삭제 정책을 삭제 표시(Soft Delete)로 변경

PR #11 merge 후, 삭제 규칙을 다시 검토해 `feature/soft-delete_261023`에서 변경했다.

### 왜

- 처음에는 환자를 지우면 진료 기록, X-ray, AI 결과까지 함께 지워지는 `CASCADE`였다.
- 의료 기록은 실수로 사라지면 복구할 수 없고, 이력으로 남겨야 하므로 **데이터를 실제로 지우지 않고 별도로 보관**하기로 했다.

### 어떻게

| 파일 | 변경 |
|---|---|
| `app/models/*.py` 5개 | `SoftDeleteMixin` 상속 → `is_deleted`, `deleted_at` 컬럼 추가 |
| `medical_records.py`, `xray_images.py`, `ai_analysis_results.py` | FK `ondelete`를 `CASCADE` → `RESTRICT`. 자식 데이터가 있으면 실제 삭제를 DB가 막음 |
| `patients.py`, `medical_records.py` | `relationship`의 `cascade="all, delete-orphan"` 제거 |
| `app/core/db/models.py` | `is_deleted`에 `server_default=text("0")` 추가. 이미 데이터가 있는 테이블에 컬럼을 추가해도 `False`로 채워짐 |
| `alembic/versions/78d9440bd099_...py` (새 파일) | 두 번째 마이그레이션. 이미 공유된 첫 번째 파일은 고치지 않음 |
| `docs/day03_db_migration.md` | 삭제 정책, 마이그레이션 목록, 테스트 결과, 트러블슈팅 갱신 |

- 마이그레이션 자동 생성 결과에 FK 이름이 `None`으로 들어가 downgrade가 불가능해서, MySQL 기본 이름(`테이블_ibfk_1`)을 직접 지정했다.

### 확인

| 항목 | 결과 |
|---|---|
| `upgrade` → `downgrade -1` → `upgrade` | 정상 |
| 새 데이터 `is_deleted` | `False` |
| 진료 기록이 있는 환자 실제 삭제 | 거부 |
| 환자 삭제 표시 | 조회 대상에서 빠지고 DB에는 보관됨 |

## 🔄 추가 변경: Swagger에 프로젝트 정보 표시

### `app/main.py` - FastAPI 앱 정보

- **왜**: Swagger 화면 제목이 기본값 "FastAPI"로만 보여 어떤 프로젝트인지, 누가 만들었는지 알 수 없었다.
- **어떻게**: `FastAPI()`에 정보를 추가했다.
  - `title`: 폐렴 환자 관리 백오피스
  - `description`: 프로젝트 소개와 팀원 4명의 GitHub 링크 표 (마크다운)
  - `contact`: 팀 레포 주소. FastAPI의 `contact`는 한 명만 넣을 수 있어 팀원 목록은 `description`에 넣었다.
- **주의**: `description` 문자열을 코드 들여쓰기에 맞춰 들여쓰면, 마크다운에서 4칸 이상 들여쓴 줄은 코드 블록이 되어 표가 그려지지 않는다. 그래서 문자열 내용은 들여쓰지 않았다.

## 👥 팀원 작업 (PR #15 ~ #17)

각자 로컬에 Docker MySQL을 띄워 마이그레이션을 적용하고, DBeaver 캡처와 학습 정리를 본인 브랜치에서 PR로 올렸다.
문서에 팀원별 칸을 미리 나눠두어 같은 파일을 고쳐도 충돌 없이 합쳐졌다.

| 팀원 | `day03_db_migration.md` 7번 | `day03_프로젝트_뜯어보기.md` 6번 |
|---|---|---|
| 김도엽 | DB 캡처 + 겪은 문제 | 2. 파일별 역할 |
| 이명석 | DB 캡처 + 겪은 문제 | 4. 모델 작성과 alembic |
| 박유정 | DB 캡처 + 겪은 문제 | 1. 디렉터리별 역할 |

### 팀원들이 겪은 문제와 해결

| 문제 | 원인 | 해결 |
|---|---|---|
| `asyncmy` 설치 실패 | Python 3.14에서 빌드 오류 | Python 3.13 환경으로 재설치 |
| `docker` 명령을 찾지 못함 | Docker Desktop이 실행되지 않음 | Docker Desktop 실행 후 터미널 재시작 |
| `git pull`이 `Aborting`으로 실패 | 로컬에서 수정한 파일이 받아올 변경과 겹침 | `git stash` → `git pull` → `git stash pop` |
| PR을 만들 수 없음 | 같은 이름의 브랜치가 이미 있어 이동하지 못하고 develop에 커밋함 | `git branch -f`로 브랜치를 커밋 위치로 옮긴 뒤 push |
| DBeaver 화면이 비어 보임 | Connections(데이터베이스 탐색기) 패널이 닫혀 있음 | Window → Connections로 다시 열기 |
| DBeaver에 엉뚱한 테이블이 보임 | 기본 예제 DB(SQLite)를 펼침 | MySQL 연결을 새로 만들어 `ai_health` 확인 |

### 팀원들이 남긴 질문 (다음 작업 때 함께 정하기)

- Python 버전을 프로젝트에서 고정해야 할까? (`.python-version`이 현재 `.gitignore`에 있어 공유되지 않음)
- 여러 명이 동시에 모델을 고치면 alembic 마이그레이션이 갈라질 수 있는데, 브랜치 전략만으로 충분할까?
- 비어 있는 `schemas/`, `services/`, `repositories/`는 언제, 어떤 순서로 채울까?

## ⏭️ 남은 작업

- [x] PR 리뷰 (박유정, 김도엽, 이명석)
- [x] 삭제 표시 변경 PR 리뷰·merge
- [x] 팀원 로컬 DB 세팅, 캡처, 학습 정리 PR
- [ ] develop → main 반영
