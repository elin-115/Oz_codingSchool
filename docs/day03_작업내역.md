# 📝 Day03 작업 내역

- 날짜: 2026-10-23
- 브랜치: `feature/db-models_261023` (PR #11), `feature/soft-delete_261023`
- 작업자: 김지연 / 리뷰: 박유정, 김도엽, 이명석

## 요약

| 구분 | 파일 수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 10개 | Enum, 모델 5개, 마이그레이션, 문서 2개, 캡처 이미지 |
| ✏️ 수정한 것 | 3개 | TimestampMixin 버그 수정, 모델 등록, README |

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

## ⏭️ 남은 작업

- [x] PR 리뷰 (박유정, 김도엽, 이명석)
- [ ] 삭제 표시 변경 PR 리뷰·merge
- [ ] 팀원 로컬 DB 세팅, 캡처, 학습 정리 PR
- [ ] develop → main 반영
