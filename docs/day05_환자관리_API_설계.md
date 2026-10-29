# 🏥 Day05 환자 관리 · 진료기록 API 설계

## 0. 개요

5일차 사용자 요구사항 정의서(REQ-PTNT-001 ~ 005, REQ-MDR-001 ~ 003, NFR-PTNT-001, NFR-MDR-001)를 바탕으로 환자 관리·진료기록 API를 설계   
API 주소와 요청·응답 필드는 템플릿 프론트엔드(`static/apis.js`, `static/pages.js`)가 호출하고 읽는 형식에 맞춤  

- Base URL: `/api/v1`
- 인증: Day04 User API와 동일. 모든 API는 `Authorization: Bearer <access_token>` 헤더가 필요하다.
- 성능: 모든 API는 3초 이내에 응답한다 (NFR-PTNT-001, NFR-MDR-001). 목록 조회는 필요한 컬럼만 조회하고, 진료기록 상세는 X-Ray 이미지를 한 번에 함께 불러온다(`selectinload`).

### API 목록

| # | 기능 | Method | Endpoint | 권한 | 요구사항 | 담당 |
|---|---|---|---|---|---|---|
| 1 | 환자 등록 | POST | `/api/v1/patients` | 의료진 | REQ-PTNT-001 | 김도엽 |
| 2 | 환자 목록 조회 (검색·필터) | GET | `/api/v1/patients` | 승인된 회원 | REQ-PTNT-002 | 김도엽 |
| 3 | 환자 상세 조회 | GET | `/api/v1/patients/{patient_id}` | 승인된 회원 | REQ-PTNT-003 | 이명석 |
| 4 | 환자 정보 수정 | PATCH | `/api/v1/patients/{patient_id}` | 승인된 회원 | REQ-PTNT-004 | 이명석 |
| 5 | 환자 정보 삭제 | DELETE | `/api/v1/patients/{patient_id}` | 승인된 회원 | REQ-PTNT-005 | 김지연 |
| 6 | 진료기록 등록 | POST | `/api/v1/medical-records` | 의료진 | REQ-MDR-001 | 김지연 |
| 7 | 환자별 진료기록 목록 조회 | GET | `/api/v1/patients/{patient_id}/medical-records` | 승인된 회원 | REQ-MDR-002 | 박유정 |
| 8 | 진료기록 상세 조회 | GET | `/api/v1/medical-records/{record_id}` | 승인된 회원 | REQ-MDR-003 | 박유정 |

> 프론트에 있는 AI 예측(`POST /medical-records/{id}/predict`, `GET /medical-records/{id}/analyses`)은 다음 Stage 범위라 이번 설계에서 제외한다.

## 1. 공통 설계

### 1-1. 권한

| 의존성 | 위치 | 조건 | 사용 API |
|---|---|---|---|
| `StaffUser` | `app/core/dependencies.py` | 대기자(`pending`)가 아닌 회원. 개발진·의료진·연구진 모두 | 2, 3, 4, 5, 7, 8 |
| `MedicalUser` | `app/core/dependencies.py` | `StaffUser` 중 **부서가 `medical team`**인 회원 | 1, 6 |

- 요구사항의 "사내 의료인 역할"은 권한(role)에 따로 없으므로 **부서(`department`)로 판단**한다. 어드민이라도 의료진 부서가 아니면 등록할 수 없다.
- 대기자는 403 `관리자 승인 후 이용할 수 있습니다.`, 의료진이 아니면 403 `의료진만 이용할 수 있습니다.`

### 1-2. 공통 코드

| 이름 | 위치 | 용도 |
|---|---|---|
| `MedicalUser` | `app/core/dependencies.py` | 의료진 확인 (1-1) |
| `PatientResponse` | `app/schemas/patients.py` | 환자 정보 응답 (1-5) |
| `MedicalRecordListResponse` | `app/schemas/medical_records.py` | 진료기록 목록 한 줄 (1-6) |
| `MedicalRecordResponse` | `app/schemas/medical_records.py` | 진료기록 상세 (1-6) |
| `get_patient_by_id` | `app/repositories/patients.py` | 환자 한 명 조회 (삭제 표시된 환자 제외). 3, 4, 5, 6, 7에서 공통 사용 |
| `get_patient_or_404` | `app/services/patients.py` | 환자가 없으면 404 `환자를 찾을 수 없습니다.` |
| `MessageResponse` | `app/schemas/users.py` | 안내 문구 응답 (Day04 공통) |

### 1-3. 공통 에러 응답

| 상태 코드 | 상황 | 예시 |
|---|---|---|
| 400 Bad Request | 업무 규칙 위반 | `{"detail": "수정할 항목을 하나 이상 입력해주세요."}` |
| 401 Unauthorized | 토큰 없음·만료·위조 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` |
| 403 Forbidden | 대기자, 의료진이 아닌 회원의 등록 | `{"detail": "의료진만 이용할 수 있습니다."}` |
| 404 Not Found | 환자·진료기록 없음 | `{"detail": "환자를 찾을 수 없습니다."}` |
| 409 Conflict | 진료 차트 넘버 중복 | `{"detail": "이미 등록된 진료 차트 넘버입니다."}` |
| 422 Unprocessable Entity | 필수 값 누락, 형식 오류 | Day04 설계 1-5와 같은 FastAPI 기본 형식 |

### 1-4. 입력값 규칙

| 항목 | 규칙 |
|---|---|
| name | 환자 이름, 2-30자 (DB `String(30)`) |
| age | 0-150 정수 |
| gender | `male` / `female` (프론트 `patient-create.html`의 `<option value>`와 같음) |
| phone_number | 하이픈 없이 `01`로 시작하는 10-11자리 숫자 (Day04 `PhoneType` 재사용) |
| chart_number | 진료 차트 넘버, 1-50자, **중복 불가** (DB `unique`) |
| symptoms | 진료된 증상, 1자 이상 |
| xray_image | 이미지 파일 (`image/png`, `image/jpeg`), 최대 10MB (이유는 3장) |

### 1-5. 환자 정보 응답 형식 (`PatientResponse`)

```json
{
  "id": 1,
  "name": "홍길동",
  "age": 45,
  "gender": "male",
  "phone_number": "01012345678",
  "created_at": "2026-10-27T10:00:00",
  "updated_at": "2026-10-27T10:00:00"
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 환자 고유 ID |
| name | string | 이름 |
| age | integer | 나이 |
| gender | string | 성별 (`male` / `female`) |
| phone_number | string | 연락처 (하이픈 없음) |
| created_at | string (datetime) | 생성일시 |
| updated_at | string (datetime) \| null | 수정일시 |

> DB 컬럼 이름은 ERD대로 `phone`이지만, 프론트가 `phone_number`로 보내고 읽으므로 **스키마에서만 `phone_number`**로 바꿔 쓴다. 응답은 `Field(validation_alias="phone")`, 요청은 service에서 `phone=data.phone_number`로 옮긴다.

### 1-6. 진료기록 응답 형식

**목록 한 줄 (`MedicalRecordListResponse`)**

```json
{
  "id": 3,
  "chart_number": "CH-20261027-001",
  "symptoms": "기침과 발열이 3일째 지속되며...",
  "created_at": "2026-10-27T10:30:00"
}
```

**상세 (`MedicalRecordResponse`)**

```json
{
  "id": 3,
  "patient_id": 1,
  "chart_number": "CH-20261027-001",
  "symptoms": "기침과 발열이 3일째 지속되며 숨이 차다.",
  "xray_image_url": "/media/xray/0f8e2c4a....png",
  "created_at": "2026-10-27T10:30:00"
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 진료 기록 ID |
| patient_id | integer | 환자 고유 ID (상세만. 프론트 "환자에게 돌아가기" 버튼에 사용) |
| chart_number | string | 진료 차트 넘버 |
| symptoms | string | 증상. **목록은 100자 초과 시 앞 100자 + `…`**, 상세는 전체 |
| xray_image_url | string \| null | 흉부 X-Ray 이미지 주소 (상세만). `<img src>`에 바로 넣는다 |
| created_at | string (datetime) | 생성일시 |

### 1-7. X-Ray 이미지 저장

- 요구사항대로 **서버가 실행되는 환경의 로컬 저장소**에 저장한다: `media/xray/{uuid}.{확장자}`
- `app/main.py`가 이미 `media` 폴더를 `/media` 주소로 열어두므로, DB `xray_images.image_url`에는 `/media/xray/{uuid}.{확장자}`를 저장해 그대로 응답한다.
- 같은 파일 이름이 겹치지 않도록 원래 파일 이름 대신 uuid를 쓴다.
- `media/`는 `.gitignore`에 넣어 업로드한 사진이 커밋되지 않게 한다.

---

## 2. API 명세

### API 1. 환자 등록

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 환자 등록 API |
| 설명 | 의료진이 환자 정보 등록 모달에서 환자를 등록한다. (REQ-PTNT-001) |
| 엔드포인트 | `/api/v1/patients` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y (`MedicalUser`) |
| 담당 | 김도엽 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer <access_token> | 로그인한 의료진 |
| Content-Type | application/json | JSON 본문 전송 |

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| name | string | Y | 이름 (2-30자) |
| age | integer | Y | 나이 (0-150) |
| gender | string | Y | `male` / `female` |
| phone_number | string | Y | 하이픈 없는 휴대폰 번호 |

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "male",
  "phone_number": "01012345678"
}
```

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 201 Created**: 생성된 환자 정보 (`PatientResponse`, 1-5 참고)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "의료진만 이용할 수 있습니다."}` | 의료진 부서가 아님 |
| 422 | 1-3 참고 | 필수 값 누락, 형식 오류 |

#### 4) 비고

- 환자 연락처는 가족이 같은 번호를 쓸 수 있으므로 중복 검사를 하지 않는다.

---

### API 2. 환자 목록 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 환자 목록 조회 API |
| 설명 | 등록된 환자 목록을 이름으로 검색하고 성별·나이 범위로 필터링한다. (REQ-PTNT-002) |
| 엔드포인트 | `/api/v1/patients` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 김도엽 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**본문 필드**: 없음

**쿼리 파라미터** (모두 선택, 쿼리 파라미터 모델 `PatientListQuery`)

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| name | string | N | 이름에 포함된 문자열 |
| gender | string | N | `male` / `female` |
| min_age | integer | N | 최소 나이 (이상) |
| max_age | integer | N | 최대 나이 (이하) |

```
GET /api/v1/patients?name=홍&gender=male&min_age=30&max_age=60
```

#### 3) 응답 (Response)

**성공 · 200 OK**: `PatientResponse` 배열 (1-5 참고). 삭제된 환자는 제외, id 순 정렬

```json
[
  {
    "id": 1,
    "name": "홍길동",
    "age": 45,
    "gender": "male",
    "phone_number": "01012345678",
    "created_at": "2026-10-27T10:00:00",
    "updated_at": "2026-10-27T10:00:00"
  }
]
```

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 400 | `{"detail": "최소 나이는 최대 나이보다 클 수 없습니다."}` | `min_age > max_age` |
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 422 | 1-3 참고 | 나이에 숫자가 아닌 값 |

#### 4) 비고

- 조건은 값이 있을 때만 붙인다 (Day04 회원 목록 검색과 같은 방식). 이름은 포함 검색(`contains`).
- 프론트는 빈 칸을 아예 보내지 않으므로, 아무 조건이 없으면 전체 목록을 준다.

---

### API 3. 환자 상세 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 환자 상세 조회 API |
| 설명 | 환자 목록의 `상세보기`로 환자 한 명의 정보를 조회한다. (REQ-PTNT-003) |
| 엔드포인트 | `/api/v1/patients/{patient_id}` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 이명석 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**경로 파라미터**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| patient_id | integer | Y | 환자 고유 ID |

**본문 필드 / 쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: 환자 정보 (`PatientResponse`, 1-5 참고)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "환자를 찾을 수 없습니다."}` | 없는 환자, 삭제된 환자 |

#### 4) 비고

- 요구사항의 확인 항목은 이름·성별·연락처·나이지만, 응답 형식을 하나로 통일하기 위해 `PatientResponse` 전체를 준다.

---

### API 4. 환자 정보 수정

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 환자 정보 수정 API |
| 설명 | 환자 상세 페이지의 `정보 수정` 모달에서 이름과 연락처를 수정한다. (REQ-PTNT-004) |
| 엔드포인트 | `/api/v1/patients/{patient_id}` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 이명석 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer <access_token> | 로그인한 회원 |
| Content-Type | application/json | JSON 본문 전송 |

**경로 파라미터**: `patient_id` (integer, 환자 고유 ID)

**본문 필드** (보낸 항목만 수정)

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| name | string | N | 이름 (2-30자) |
| phone_number | string | N | 하이픈 없는 휴대폰 번호 |

```json
{
  "name": "홍길동",
  "phone_number": "01098765432"
}
```

#### 3) 응답 (Response)

**성공 · 200 OK**: 수정된 환자 정보 (`PatientResponse`, 1-5 참고). `updated_at`이 바뀐다.

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 400 | `{"detail": "수정할 항목을 하나 이상 입력해주세요."}` | 빈 요청 `{}` |
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "환자를 찾을 수 없습니다."}` | 없는 환자, 삭제된 환자 |
| 422 | 1-3 참고 | 형식 오류 |

#### 4) 비고

- 나이·성별은 요구사항상 수정할 수 없으므로 요청 스키마에 넣지 않는다 (보내도 무시된다).
- 프론트는 수정 모달의 두 값을 항상 함께 보낸다.

---

### API 5. 환자 정보 삭제

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 환자 정보 삭제 API |
| 설명 | 환자와 관련된 진료기록, X-Ray 이미지를 함께 영구 삭제한다. (REQ-PTNT-005) |
| 엔드포인트 | `/api/v1/patients/{patient_id}` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 김지연 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**경로 파라미터**: `patient_id` (integer, 환자 고유 ID)

**본문 필드 / 쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK** (`MessageResponse`)

```json
{
  "message": "환자 정보와 관련 데이터가 모두 삭제되었습니다."
}
```

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "환자를 찾을 수 없습니다."}` | 없는 환자 |

#### 4) 비고

- **영구 삭제(Hard Delete)** 로 처리한다. 3장 참고.
- FK가 `RESTRICT`이므로 자식부터 지운다: AI 분석 결과 → X-Ray 이미지 행 → 진료기록 → 환자. 한 트랜잭션에서 처리해 중간에 실패하면 모두 되돌린다.
- DB 삭제가 성공한 뒤 `media/xray/`의 이미지 파일도 지운다. 파일이 이미 없으면 무시한다.
- 확인 팝업(`확인했습니다`)은 프론트가 띄우므로 API는 한 번만 호출된다.

---

### API 6. 진료기록 등록

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 진료기록 등록 API |
| 설명 | 의료진이 환자의 X-Ray 사진을 포함한 진료기록을 등록한다. (REQ-MDR-001) |
| 엔드포인트 | `/api/v1/medical-records` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y (`MedicalUser`) |
| 담당 | 김지연 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer <access_token> | 로그인한 의료진 |
| Content-Type | multipart/form-data | 프론트가 `FormData`로 파일과 함께 전송 |

**본문 필드 (form)**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| patient_id | integer | Y | 환자 고유 ID |
| chart_number | string | N | 진료 차트 넘버 (1-50자, 중복 불가), 비우면 자동 발급 |
| symptoms | string | Y | 진료된 증상 |
| xray_image | file | Y | 흉부 X-Ray 이미지 (png, jpeg, 최대 10MB) |

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 201 Created**: 생성된 진료기록 상세 (`MedicalRecordResponse`, 1-6 참고)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 400 | `{"detail": "png 또는 jpeg 이미지만 업로드할 수 있습니다."}` | 이미지가 아닌 파일 |
| 400 | `{"detail": "이미지는 10MB 이하만 업로드할 수 있습니다."}` | 파일이 너무 큼 |
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "의료진만 이용할 수 있습니다."}` | 의료진 부서가 아님 |
| 404 | `{"detail": "환자를 찾을 수 없습니다."}` | 없는 환자 |
| 409 | `{"detail": "이미 등록된 진료 차트 넘버입니다."}` | 차트 넘버 중복 |
| 422 | 1-3 참고 | 필수 값 누락 |

#### 4) 비고

- 진료기록(`medical_records`)과 X-Ray 이미지(`xray_images`) 두 테이블에 저장한다. 업로더(`uploader_id`)는 로그인한 의료진이다.
- `xray_images.shooting_datetime`(촬영일시)은 필수지만 프론트 입력 칸이 없으므로 **업로드한 시각**으로 저장한다.
- 파일을 먼저 저장하고 DB 저장이 실패하면 저장한 파일을 지운다 (사진만 남는 일을 막음).
- 이미지 미리보기는 프론트(`FileReader`)가 처리한다.

---

### API 7. 환자별 진료기록 목록 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 환자별 진료기록 목록 조회 API |
| 설명 | 환자 상세 페이지의 진료 기록 목록 섹션에서 해당 환자의 진료기록을 조회한다. (REQ-MDR-002) |
| 엔드포인트 | `/api/v1/patients/{patient_id}/medical-records` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 박유정 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**경로 파라미터**: `patient_id` (integer, 환자 고유 ID)

**본문 필드 / 쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: `MedicalRecordListResponse` 배열 (1-6 참고). 최신순(생성일시 내림차순)

```json
[
  {
    "id": 3,
    "chart_number": "CH-20261027-001",
    "symptoms": "기침과 발열이 3일째 지속되며...",
    "created_at": "2026-10-27T10:30:00"
  }
]
```

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "환자를 찾을 수 없습니다."}` | 없는 환자 |

#### 4) 비고

- 환자가 있는데 진료기록이 없으면 빈 배열 `[]`을 준다 (404 아님).
- 증상이 100자를 넘으면 앞 100자 + `…`로 자른다. 프론트는 받은 값을 그대로 보여주므로 **서버에서** 자른다.

---

### API 8. 진료기록 상세 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 진료기록 상세 조회 API |
| 설명 | 진료기록 목록의 `상세보기`로 진료기록 한 건과 X-Ray 이미지를 조회한다. (REQ-MDR-003) |
| 엔드포인트 | `/api/v1/medical-records/{record_id}` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 박유정 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**경로 파라미터**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| record_id | integer | Y | 진료 기록 ID |

**본문 필드 / 쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: 진료기록 상세 (`MedicalRecordResponse`, 1-6 참고)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "진료 기록을 찾을 수 없습니다."}` | 없는 진료기록 |

#### 4) 비고

- `xray_image_url`은 진료기록에 연결된 `xray_images`의 `image_url`이다. repository에서 `selectinload(MedicalRecord.xray_images)`로 함께 불러와 쿼리를 한 번에 끝낸다.
- 진료기록 상세 페이지는 AI 예측 결과(`/analyses`)도 함께 부르는데, 이 API는 다음 Stage에서 만든다. 그 전까지는 페이지에 "Not Found" 알림이 뜰 수 있다.

---

## 3. 요구사항과 다르게 결정한 부분 / 추가로 결정한 부분

### 환자 삭제: 영구 삭제 (Soft Delete 아님)

- **요구사항**: REQ-PTNT-005 "해당 환자와 관련된 진료기록, X-Ray 이미지도 함께 **영구 삭제**한다."
- **결정**: 요구사항대로 **실제로 행과 파일을 지운다.** (팀 논의 10/27)
- **이유**
  1. 회원 탈퇴는 "즉시 삭제"라는 표현이라 조교님께 확인받고 Soft Delete + 개인정보 삭제로 했지만, 환자 삭제는 **"영구 삭제"라고 명시**되어 있다.
  2. 환자 정보와 X-Ray는 민감한 의료 개인정보라, 삭제를 요청하면 남기지 않는 쪽이 맞다.
- 모델의 `is_deleted` 컬럼은 그대로 두고, 조회할 때는 Day04처럼 `is_deleted = False` 조건을 계속 건다 (나중에 Soft Delete로 바꿔도 조회 코드는 그대로 쓸 수 있게).

### 사내 의료인 = 의료진 부서

- 권한(role)에는 의료인이 없으므로 부서가 `medical team`인 승인된 회원을 의료인으로 본다 (1-1).

### 연락처 필드 이름 `phone_number`

- DB 컬럼은 ERD대로 `phone`, API는 프론트에 맞춰 `phone_number` (1-5).

### X-Ray 촬영일시

- 프론트에 입력 칸이 없어 업로드한 시각으로 저장한다 (API 6 비고).

### X-Ray 이미지: png·jpeg, 10MB 이하

- **요구사항**: 형식·크기 제한 없음 (REQ-MDR-001)
- **결정**: png·jpeg만, 10MB 이하 (팀 논의 10/27)
- **이유**
  1. 제한이 없으면 큰 파일이 서버 디스크를 채우고 업로드가 느려져, 3초 응답(NFR-MDR-001)을 지키기 어렵다.
  2. jpg·png로 변환한 흉부 X-Ray는 대부분 수 MB 이하라 10MB면 충분하다.
  3. 병원 원본 형식(DICOM)은 이번 과제 범위 밖이라 받지 않는다. 프론트 미리보기도 일반 이미지만 지원한다.
- 프론트 진료기록 등록 화면에도 라벨 `(png, jpg, 10MB 이하)`와 `accept="image/png, image/jpeg"`로 안내한다.

## 4. 코드 구조와 분담

```
app/
├── core/
│   └── dependencies.py          # + MedicalUser (의료진 확인)
├── schemas/
│   ├── patients.py              # 환자 요청·응답
│   └── medical_records.py       # 진료기록 요청·응답
├── repositories/
│   ├── patients.py              # 환자 DB 조회·저장·삭제
│   └── medical_records.py       # 진료기록·X-Ray DB 조회·저장
├── services/
│   ├── patients.py
│   └── medical_records.py
└── apis/
    ├── patients.py              # /api/v1/patients (+ /{patient_id}/medical-records)
    └── medical_records.py       # /api/v1/medical-records
```

| 담당 | API |
|---|---|
| 김지연 | 공통 뼈대(설계 문서, `MedicalUser`, 응답 스키마, 공통 조회 함수, 라우터 등록) + 환자 삭제 + 진료기록 등록 |
| 김도엽 | 환자 등록 + 환자 목록 조회(검색·필터) |
| 박유정 | 환자별 진료기록 목록 조회 + 진료기록 상세 조회 |
| 이명석 | 환자 상세 조회 + 환자 정보 수정 |

- 김지연이 뼈대를 먼저 merge하고, 팀원은 각자 develop에서 브랜치를 따서 작업한다. 김지연의 API 2개도 뼈대 merge 후 같은 방식으로 PR을 올린다.
- 팀원은 각 파일의 `# ===== [이름] ... =====` 주석 아래에만 작성해 충돌을 줄인다.
- 작성 순서: **schemas → repositories → services → apis**
- 의존성은 Day04처럼 **타입 자리에 바로** 쓴다: `user: StaffUser` (O), `Depends(StaffUser)` (X)
- PR을 올리기 전에 Swagger와 **프론트 화면**에서 직접 확인한다. 프론트가 보내는 필드 이름은 `static/pages.js`에서 확인한다.

## 📚 참고 자료

- [FastAPI 쿼리 매개변수 모델](https://fastapi.tiangolo.com/ko/tutorial/query-param-models/)
- [FastAPI 경로 매개변수](https://fastapi.tiangolo.com/ko/tutorial/path-params/)
- [FastAPI 폼 데이터](https://fastapi.tiangolo.com/ko/tutorial/request-forms/)
- [FastAPI 파일 요청 (UploadFile)](https://fastapi.tiangolo.com/ko/tutorial/request-files/)
- [SQLAlchemy selectinload](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#selectin-eager-loading)
- [Pydantic Field alias](https://docs.pydantic.dev/latest/concepts/alias/)
