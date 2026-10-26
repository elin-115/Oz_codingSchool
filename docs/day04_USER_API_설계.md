# 👤 Day04 User API 설계

## 1. 개요

4일차 사용자 요구사항 정의서(REQ-USER-001 ~ 009, NFR-USER-001 ~ 003)를 바탕으로 User API를 설계했다.
API 주소와 요청 형식은 템플릿 프론트엔드(`static/apis.js`)가 호출하는 형식에 맞췄다.

- Base URL: `/api/v1`
- 인증: JWT (Access Token은 `Authorization: Bearer` 헤더, Refresh Token은 http_only 쿠키)
- 응답 형식: JSON (비밀번호는 어떤 응답에도 포함하지 않음)

### API 목록

| # | 기능 | Method | Endpoint | 권한 | 요구사항 | 담당 |
|---|---|---|---|---|---|---|
| 1 | 회원가입 | POST | `/users/signup` | 누구나 | REQ-USER-001 | 김지연 |
| 2 | 로그인 | POST | `/users/login` | 누구나 | REQ-USER-002, NFR-USER-001 | 김도엽 |
| 3 | 토큰 재발급 | POST | `/users/refresh` | 쿠키 | NFR-USER-001 | 김도엽 |
| 4 | 로그아웃 | POST | `/users/logout` | 로그인 | REQ-USER-003 | 김도엽 |
| 5 | 내 정보 조회 | GET | `/users/me` | 로그인 | REQ-USER-006 | 박유정 |
| 6 | 내 정보 수정 | PATCH | `/users/me` | 로그인 | REQ-USER-007 | 박유정 |
| 7 | 비밀번호 변경 | PATCH | `/users/me/password` | 로그인 | REQ-USER-008 | 이명석 |
| 8 | 회원 탈퇴 | DELETE | `/users/me` | 로그인 | REQ-USER-009 | 박유정 |
| 9 | 회원 목록 조회 | GET | `/admin/users` | 어드민 | REQ-USER-004 | 이명석 |
| 10 | 회원 권한 변경 | PATCH | `/admin/users/role` | 어드민 | REQ-USER-005 | 이명석 |

## 2. 인증 / 인가 설계 (NFR-USER-001)

### 토큰

| 구분 | 만료 | 전달 방법 | 페이로드 |
|---|---|---|---|
| Access Token | 30분 | 응답 body → 클라이언트가 `Authorization: Bearer <token>` 헤더로 전송 | `sub`(user_id), `type`("access"), `exp` |
| Refresh Token | 7일 | `Set-Cookie` http_only 쿠키 (`refresh_token`) | `sub`(user_id), `type`("refresh"), `exp` |

- 페이로드에는 최소 식별 정보인 **user_id만** 담는다. `type`은 Access Token 자리에 Refresh Token을 넣는 것을 막기 위한 구분값이고, `exp`는 만료 시각이다.
- Refresh Token은 http_only 쿠키라 JavaScript에서 읽을 수 없다.
- Access Token이 만료되면 프론트가 `/users/refresh`를 호출해 재발급받고, Refresh Token도 만료되면 401을 받아 로그인 페이지로 이동한다.

### 권한

| 권한 | 값 | 접근 범위 |
|---|---|---|
| 대기자 | `pending` | 마이페이지(내 정보 조회·수정, 비밀번호 변경, 탈퇴)만 가능. 회원가입 직후 기본값 |
| 스태프 | `staff` | 흉부 X-ray 관련 읽기·쓰기·수정 |
| 어드민 | `admin` | 모든 데이터 + 회원 관리 |

### 공통 의존성 (`app/core/dependencies.py`)

| 이름 | 용도 | 실패 시 |
|---|---|---|
| `CurrentUser` | 로그인한 회원 (토큰 검증 + 탈퇴·비활성 회원 제외) | 401 |
| `StaffUser` | 스태프 이상 (대기자 제외) | 403 |
| `AdminUser` | 어드민만 | 403 |

### 공통 에러

| 상태 코드 | 상황 |
|---|---|
| 400 | 요청 값이 비어 있거나 규칙에 맞지 않는 업무 오류 (예: 수정 항목 없음, 기존 비밀번호 불일치) |
| 401 | 토큰이 없거나 만료·위조됨, 로그인 실패 |
| 403 | 권한 부족 |
| 404 | 대상 회원 없음 |
| 409 | 이메일·휴대폰 번호 중복 |
| 422 | 입력 형식 검증 실패 (FastAPI 기본) |

## 3. 입력값 규칙

| 항목 | 규칙 |
|---|---|
| 이메일 | 정규표현식 형식 검사, 최대 255자, 중복 불가 |
| 비밀번호 | 8-20자, 대문자·특수문자 각 1개 이상. **Argon2로 해싱해 저장** |
| 이름 | 2-20자 |
| 부서 | `developer`(개발) / `medical team`(의료) / `researcher`(연구) |
| 성별 | `male` / `female` |
| 휴대폰 번호 | 하이픈 없이 `01`로 시작하는 10-11자리 숫자, 중복 불가 |

> 부서·성별 값은 프론트 `signup.html`의 `<option value>`와 같다.

## 4. API 명세

### 1) 회원가입 `POST /api/v1/users/signup`

- **권한**: 누구나
- **Request Body (JSON)**

```json
{
  "email": "doctor@example.com",
  "password": "Abcdefg1!",
  "name": "김의사",
  "department": "medical team",
  "gender": "female",
  "phone_number": "01012345678"
}
```

- **Response 201**

```json
{
  "id": 1,
  "email": "doctor@example.com",
  "name": "김의사",
  "department": "medical team",
  "gender": "female",
  "phone_number": "01012345678",
  "role": "pending",
  "is_active": true
}
```

- **Error**: 409 이메일 중복 / 409 휴대폰 번호 중복 / 422 입력 규칙 위반
- 가입 직후 권한은 `pending`. 어드민이 권한을 바꿔야 서비스를 이용할 수 있다.

### 2) 로그인 `POST /api/v1/users/login`

- **권한**: 누구나
- **Request Body (form-data)**: 프론트가 `FormData`로 보내고 Swagger Authorize도 이 형식을 쓰므로 `OAuth2PasswordRequestForm` 사용

| 필드 | 값 |
|---|---|
| `username` | 이메일 |
| `password` | 비밀번호 |

- **Response 200**

```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

- **Set-Cookie**: `refresh_token=<token>; HttpOnly; Max-Age=604800; Path=/api/v1/users; SameSite=Lax`
- **Error**: 401 이메일 또는 비밀번호 불일치 (어느 쪽이 틀렸는지 알려주지 않음) / 401 비활성·탈퇴 회원

### 3) 토큰 재발급 `POST /api/v1/users/refresh`

- **권한**: `refresh_token` 쿠키
- **Request Body**: 없음
- **Response 200**

```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

- **Error**: 401 쿠키 없음 / 만료 / 위조 / 회원 없음 → 프론트는 로그인 페이지로 이동

### 4) 로그아웃 `POST /api/v1/users/logout`

- **권한**: 로그인
- **Response 200**: `{ "message": "로그아웃되었습니다." }`
- `refresh_token` 쿠키를 삭제한다. Access Token은 서버에 저장하지 않으므로 프론트가 지운다.

### 5) 내 정보 조회 `GET /api/v1/users/me`

- **권한**: 로그인 (대기자 포함)
- **Response 200**: 회원가입 응답과 같은 형식 (`id`, `email`, `name`, `department`, `gender`, `phone_number`, `role`, `is_active`)

### 6) 내 정보 수정 `PATCH /api/v1/users/me`

- **권한**: 로그인
- **Request Body (JSON, 부분 수정)**: 보낸 항목만 수정

```json
{ "department": "researcher", "phone_number": "01098765432" }
```

- **Response 200**: 수정된 회원 정보
- **Error**: 400 수정할 항목 없음 / 409 휴대폰 번호 중복 / 422 형식 위반
- 수정 가능한 항목은 **부서, 휴대폰 번호**뿐이다. 다른 항목은 무시한다.

### 7) 비밀번호 변경 `PATCH /api/v1/users/me/password`

- **권한**: 로그인
- **Request Body (JSON)**

```json
{ "old_password": "Abcdefg1!", "new_password": "Newpass1!" }
```

- **Response 200**: `{ "message": "비밀번호가 변경되었습니다." }`
- **Error**: 400 기존 비밀번호 불일치 / 400 새 비밀번호가 기존과 같음 / 422 새 비밀번호 규칙 위반
- 기존 비밀번호를 `verify_password`로 확인한 뒤, 새 비밀번호를 해싱해 저장한다.

### 8) 회원 탈퇴 `DELETE /api/v1/users/me`

- **권한**: 로그인
- **Response 204**
- 처리 내용 (아래 5번 결정 참고)
  - `is_deleted = True`, `deleted_at = 현재 시각`, `is_active = False`
  - 개인정보 즉시 삭제: 이메일·휴대폰 번호·이름을 식별할 수 없는 값으로 바꾸고 비밀번호 해시도 지움
  - `refresh_token` 쿠키 삭제
- 탈퇴 후 같은 토큰으로 요청하면 401 (`CurrentUser`가 탈퇴 회원을 제외함)

### 9) 회원 목록 조회 `GET /api/v1/admin/users`

- **권한**: 어드민
- **Query Parameter** (모두 선택)

| 이름 | 설명 |
|---|---|
| `query` | 이메일 또는 이름에 포함된 문자열로 검색 |
| `department` | `developer` / `medical team` / `researcher` |

- **Response 200**: 회원 목록 배열 (`id`, `email`, `name`, `department`, `gender`, `phone_number`, `role`, `is_active`). 탈퇴 회원은 제외
- **Error**: 401 / 403

### 10) 회원 권한 변경 `PATCH /api/v1/admin/users/role`

- **권한**: 어드민
- **Request Body (JSON)**

```json
{ "user_id": 2, "new_role": "staff" }
```

- **Response 200**: 변경된 회원 정보
- **Error**: 401 / 403 / 404 대상 회원 없음 / 400 본인 권한 변경 (마지막 어드민이 스스로 권한을 내려 관리자가 사라지는 것을 막기 위함) / 422 `new_role` 값 오류

## 5. 요구사항과 다르게 결정한 부분

### 회원 탈퇴: 즉시 삭제 대신 삭제 표시 + 개인정보 삭제

- **요구사항**: REQ-USER-009 "회원탈퇴 시 Database에서 회원과 관련된 정보는 모두 즉시 삭제한다."
- **결정**: 행을 지우지 않고 삭제 표시(Soft Delete)를 하되, **개인정보는 즉시 지운다.**
- **이유**
  1. Day03에 팀이 의료 기록 보존을 위해 모든 테이블을 Soft Delete로 결정했다.
  2. `xray_images.uploader_id`가 `RESTRICT`라, 이미지를 업로드한 회원은 DB가 실제 삭제를 막는다. 행을 지우면 "누가 이 X-ray를 올렸는가"라는 의료 기록의 출처도 사라진다.
  3. 대신 이메일·휴대폰 번호·이름·비밀번호를 지워 요구사항의 취지(회원 정보 즉시 삭제)를 지킨다. 이메일과 휴대폰 번호가 비워지므로 같은 정보로 재가입도 가능하다.

## 6. 코드 구조와 분담

```
app/
├── core/
│   ├── config.py          # JWT 설정 (SECRET_KEY, 만료 시간)
│   ├── security.py        # 비밀번호 해싱(Argon2), JWT 발급·검증
│   └── dependencies.py    # CurrentUser, StaffUser, AdminUser
├── schemas/users.py       # 요청·응답 Pydantic 모델, 입력값 검증
├── repositories/users.py  # DB 조회·저장
├── services/users.py      # 비즈니스 로직
└── apis/
    ├── users.py           # /api/v1/users
    └── admin.py           # /api/v1/admin
```

- 김지연이 공통 코드(설정, 보안, 의존성, 응답 스키마, 라우터 등록)와 회원가입을 먼저 작성해 merge한다.
- 팀원은 각 파일의 `# ===== [이름] ... =====` 주석 아래에만 작성해 충돌을 줄인다.
- 작성 순서: **schemas → repositories → services → apis** (Day03 뜯어보기 5번)

## 📚 참고 자료

- [FastAPI 요청 본문 (Pydantic BaseModel)](https://fastapi.tiangolo.com/ko/tutorial/body/#import-pydantics-basemodel)
- [FastAPI 쿼리 매개변수 모델](https://fastapi.tiangolo.com/ko/tutorial/query-param-models/)
- [Pydantic AfterValidator](https://pydantic.dev/docs/validation/latest/api/pydantic/functional_validators/#pydantic.functional_validators.AfterValidator)
- [FastAPI JWT 인증 - suwani](https://suwani.tistory.com/188)
- [FastAPI Argon2 비밀번호 해싱 - chaechae](https://chaechae.life/blog/fastapi-password-hasing-with-agron2)
