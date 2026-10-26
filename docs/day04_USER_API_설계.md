# 👤 Day04 User API 설계

## 0. 개요

사용자 요구사항 정의서(REQ-USER-001 ~ 009, NFR-USER-001 ~ 003)를 바탕으로 User API를 설계   
API 주소와 요청 형식은 템플릿 프론트엔드(`static/apis.js`)가 호출하는 형식에 맞춤  

- Base URL: `/api/v1`
- 인증: JWT (Access Token은 `Authorization: Bearer` 헤더, Refresh Token은 http_only 쿠키)
- 비밀번호는 어떤 응답에도 포함하지 않는다.

### API 목록

| # | 기능 | Method | Endpoint | 인증 | 요구사항 | 담당 |
|---|---|---|---|---|---|---|
| 1 | 회원가입 | POST | `/api/v1/users/signup` | N | REQ-USER-001 | 김지연 |
| 2 | 로그인 | POST | `/api/v1/users/login` | N | REQ-USER-002, NFR-USER-001 | 김도엽 |
| 3 | 토큰 재발급 | POST | `/api/v1/users/refresh` | 쿠키 | NFR-USER-001 | 김지연 |
| 4 | 로그아웃 | POST | `/api/v1/users/logout` | N | REQ-USER-003 | 김도엽 |
| 5 | 내 정보 조회 | GET | `/api/v1/users/me` | Y | REQ-USER-006 | 박유정 |
| 6 | 내 정보 수정 | PATCH | `/api/v1/users/me` | Y | REQ-USER-007 | 박유정 |
| 7 | 비밀번호 변경 | PATCH | `/api/v1/users/me/password` | Y | REQ-USER-008 | 이명석 |
| 8 | 회원 탈퇴 | DELETE | `/api/v1/users/me` | Y | REQ-USER-009 | 박유정 |
| 9 | 회원 목록 조회 | GET | `/api/v1/admin/users` | Y (어드민) | REQ-USER-004 | 이명석, 김지연(검색) |
| 10 | 회원 권한 변경 | PATCH | `/api/v1/admin/users/role` | Y (어드민) | REQ-USER-005 | 이명석 |

## 1. 공통 설계

### 1-1. 인증 / 인가 (NFR-USER-001)

| 구분 | 만료 | 전달 방법 | 페이로드 |
|---|---|---|---|
| Access Token | 30분 | 응답 body → `Authorization: Bearer <token>` 헤더로 전송 | `sub`(user_id), `type`("access"), `exp` |
| Refresh Token | 7일 | `Set-Cookie` http_only 쿠키 `refresh_token` | `sub`(user_id), `type`("refresh"), `exp` |

- 페이로드에는 최소 식별 정보인 **user_id만** 담는다. `type`은 Access 자리에 Refresh를 넣는 것을 막는 구분값, `exp`는 만료 시각이다.
- Access Token이 만료되면 프론트가 토큰 재발급 API를 호출하고, Refresh Token도 만료되면 401을 받아 로그인 페이지로 이동한다.

### 1-2. 권한

| 권한 | 값 | 접근 범위 |
|---|---|---|
| 대기자 | `pending` | 마이페이지(내 정보 조회·수정, 비밀번호 변경, 탈퇴)만 가능. 가입 직후 기본값 |
| 스태프 | `staff` | 흉부 X-ray 관련 읽기·쓰기·수정 |
| 어드민 | `admin` | 모든 데이터 + 회원 관리 |

### 1-3. 공통 코드

| 이름 | 위치 | 용도 |
|---|---|---|
| `CurrentUser` | `app/core/dependencies.py` | 로그인한 회원. 토큰 없음·만료·위조, 탈퇴 회원은 401, 비활성 회원은 403 |
| `StaffUser` | `app/core/dependencies.py` | 대기자면 403 |
| `AdminUser` | `app/core/dependencies.py` | 어드민이 아니면 403 |
| `set_refresh_cookie` / `delete_refresh_cookie` | `app/core/security.py` | Refresh Token 쿠키 심기 / 지우기 (이름·path를 한 곳에서 관리) |
| `UserResponse` | `app/schemas/users.py` | 회원 정보 응답 |
| `TokenResponse` | `app/schemas/users.py` | 로그인·토큰 재발급 응답 (`access_token`, `token_type`, `expires_in`) |
| `MessageResponse` | `app/schemas/users.py` | 안내 문구 응답 |

### 1-4. 공통 요청 Headers

| Key | Value | 사용 |
|---|---|---|
| `Authorization` | `Bearer <access_token>` | 인증이 필요한 모든 API |
| `Content-Type` | `application/json` | JSON 본문을 보내는 API |
| `Content-Type` | `application/x-www-form-urlencoded` 또는 `multipart/form-data` | 로그인 |

### 1-5. 공통 에러 응답

| 상태 코드 | 상황 | 예시 |
|---|---|---|
| 400 Bad Request | 업무 규칙 위반 | `{"detail": "수정할 항목을 하나 이상 입력해주세요."}` |
| 401 Unauthorized | 토큰 없음·만료·위조, 로그인 실패, 탈퇴 회원 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` |
| 403 Forbidden | 권한 부족, 비활성 회원 | `{"detail": "관리자 권한이 필요합니다."}` |
| 404 Not Found | 대상 회원 없음 | `{"detail": "회원을 찾을 수 없습니다."}` |
| 409 Conflict | 이메일·휴대폰 번호 중복 | `{"detail": "이미 사용 중인 이메일입니다."}` |
| 422 Unprocessable Entity | 필수 값 누락, 입력 형식 오류 | 아래 참고 |

**422 응답 형식** (FastAPI 기본)

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| detail | array | 입력값 검증 오류 목록 |
| detail[].loc | array | 오류가 발생한 필드 위치 |
| detail[].msg | string | 오류 내용 |
| detail[].type | string | 오류 종류 |

### 1-6. 입력값 규칙

| 항목 | 규칙 |
|---|---|
| email | 정규표현식 형식 검사, 최대 255자, 중복 불가 |
| password | 8-20자, 대문자·특수문자 각 1개 이상. **Argon2로 해싱해 저장** |
| name | 2-20자 |
| department | `developer`(개발) / `medical team`(의료) / `researcher`(연구) |
| gender | `male` / `female` |
| phone_number | 하이픈 없이 `01`로 시작하는 10-11자리 숫자, 중복 불가 |

> department·gender 값은 프론트 `signup.html`의 `<option value>`와 같다.

### 1-7. 회원 정보 응답 형식 (`UserResponse`)

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

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 회원 고유 ID |
| email | string | 이메일 |
| name | string | 이름 |
| department | string | 부서 (`developer` / `medical team` / `researcher`) |
| gender | string | 성별 (`male` / `female`) |
| phone_number | string | 휴대폰 번호 |
| role | string | 권한 (`pending` / `staff` / `admin`) |
| is_active | boolean | 계정 활성화 여부 |

---

## 2. API 명세

### API 1. 회원가입

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원가입 API |
| 설명 | 사내 의료인, 연구진, 개발 실무진이 회원가입을 한다. (REQ-USER-001) |
| 엔드포인트 | `/api/v1/users/signup` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |
| 담당 | 김지연 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/json | JSON 본문 전송 |

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| email | string | Y | 이메일 (형식 검사, 중복 불가) |
| password | string | Y | 비밀번호 (8-20자, 대문자·특수문자 포함) |
| name | string | Y | 이름 (2-20자) |
| department | string | Y | `developer` / `medical team` / `researcher` |
| gender | string | Y | `male` / `female` |
| phone_number | string | Y | 하이픈 없는 휴대폰 번호 (중복 불가) |

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

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 201 Created**: 생성된 회원 정보 (`UserResponse`, 1-7 참고)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 409 | `{"detail": "이미 사용 중인 이메일입니다."}` | 이메일 중복 |
| 409 | `{"detail": "이미 사용 중인 휴대폰 번호입니다."}` | 휴대폰 번호 중복 |
| 422 | 1-5 참고 | 필수 값 누락, 형식 오류 |

#### 4) 비고

- 가입 직후 권한은 `pending`(대기자). 어드민이 권한을 바꿔야 마이페이지 외 서비스를 이용할 수 있다.
- 비밀번호는 Argon2로 해싱해 저장하고 응답에 포함하지 않는다.

---

### API 2. 로그인

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 로그인 API |
| 설명 | 이메일과 비밀번호로 로그인하고 JWT를 발급받는다. (REQ-USER-002, NFR-USER-001) |
| 엔드포인트 | `/api/v1/users/login` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |
| 담당 | 김도엽 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/x-www-form-urlencoded (또는 multipart/form-data) | 프론트가 `FormData`로 전송, Swagger Authorize도 같은 형식 |

**본문 필드 (form)**: `OAuth2PasswordRequestForm` 사용

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| username | string | Y | 이메일 (OAuth2 규격상 필드 이름이 `username`) |
| password | string | Y | 비밀번호 |

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK** (`TokenResponse`)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| access_token | string | 30분 동안 유효한 JWT 액세스 토큰 |
| token_type | string | 토큰 인증 방식, `bearer` |
| expires_in | integer | 액세스 토큰 만료 시간, 1800초 |

**응답 Headers**

| Key | 예시 값 | 설명 |
|---|---|---|
| Set-Cookie | `refresh_token=<JWT>; HttpOnly; Max-Age=604800; Path=/api/v1/users; SameSite=lax` | 유효기간 7일의 JWT 리프레시 토큰 (`set_refresh_cookie`) |

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "이메일 또는 비밀번호가 일치하지 않습니다."}` | 없는 이메일, 비밀번호 불일치, 탈퇴 회원 |
| 403 | `{"detail": "비활성화된 사용자입니다."}` | `is_active = false` |
| 422 | 1-5 참고 | username 또는 password 누락 |

#### 4) 비고

- 이메일과 비밀번호 중 어느 쪽이 틀렸는지 알려주지 않는다. (계정 존재 여부 노출 방지)
- 대기자(`pending`)도 로그인할 수 있다. 마이페이지를 써야 하기 때문이다.
- 예시 명세서의 `user` 정보는 응답에 넣지 않는다. 프론트(`static/app.js`)가 로그인 직후 `/users/me`로 회원 정보를 따로 받아오기 때문에, 넣으면 같은 정보를 두 API에서 관리하게 된다.
- `expires_in`은 `TokenResponse`가 설정값(`ACCESS_TOKEN_EXPIRE_MINUTES`)으로 자동 계산하므로 직접 넣지 않아도 된다.
- 로컬은 http라 `Secure`를 빼고, https로 배포할 때 `secure=True`로 바꾼다.

---

### API 3. 토큰 재발급

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 토큰 재발급 API |
| 설명 | 쿠키의 Refresh Token으로 새 Access Token을 발급한다. (NFR-USER-001) |
| 엔드포인트 | `/api/v1/users/refresh` |
| 메서드 | `POST` |
| 인증 필요 여부 | Refresh Token 쿠키 |
| 담당 | 김지연 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Cookie | `refresh_token=<JWT>` | 브라우저가 자동으로 전송 |

**본문 필드**: 없음
**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK** (`TokenResponse`): 로그인 응답과 같은 형식

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "다시 로그인해주세요."}` | 쿠키 없음, 만료, 위조, 탈퇴 회원 |
| 403 | `{"detail": "비활성화된 사용자입니다."}` | `is_active = false` |

#### 4) 비고

- 쿠키는 `request.cookies.get(REFRESH_COOKIE_NAME)`으로 읽는다.
- 401을 받으면 프론트(`static/apis.js`)가 로그아웃 처리 후 로그인 페이지로 이동한다.

---

### API 4. 로그아웃

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 로그아웃 API |
| 설명 | 로그인한 사용자가 로그아웃한다. (REQ-USER-003) |
| 엔드포인트 | `/api/v1/users/logout` |
| 메서드 | `POST` |
| 인증 필요 여부 | N (Refresh Token 쿠키만 삭제) |
| 담당 | 김도엽 |

#### 2) 요청 (Request)

**Headers**: 없음 (브라우저가 `refresh_token` 쿠키를 자동으로 보냄)

**본문 필드**: 없음
**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK** (`MessageResponse`)

```json
{ "message": "로그아웃되었습니다." }
```

**응답 Headers**

| Key | 예시 값 | 설명 |
|---|---|---|
| Set-Cookie | `refresh_token=""; Max-Age=0; Path=/api/v1/users` | 리프레시 토큰 쿠키 삭제 (`delete_refresh_cookie`) |

**실패**: 없음 (토큰이 없거나 만료돼도 항상 200)

#### 4) 비고

- Access Token은 서버에 저장하지 않으므로 프론트가 지운다. 로그아웃 후 로그인 페이지로 이동한다.
- 처음에는 인증이 필요하도록(Y) 설계했으나, 통합 테스트에서 회원 탈퇴 직후 프론트가 로그아웃을 호출하면 401 → 토큰 재발급 실패 → 다시 로그아웃이 반복되는 문제를 발견했다. 로그아웃은 내 브라우저의 쿠키만 지우는 동작이라 인증 없이도 안전하므로 인증을 빼도록 수정했다.

---

### API 5. 내 정보 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 내 정보 조회 API |
| 설명 | 로그인한 사용자가 마이페이지에서 본인 정보를 조회한다. (REQ-USER-006) |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (대기자 포함) |
| 담당 | 박유정 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer `<access_token>` | 로그인 사용자 확인 |

**본문 필드**: 없음
**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: 본인 회원 정보 (`UserResponse`, 1-7 참고)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 토큰 없음·만료 |
| 403 | `{"detail": "비활성화된 사용자입니다."}` | `is_active = false` |

#### 4) 비고

- `CurrentUser`가 돌려주는 회원을 그대로 응답하면 된다.

---

### API 6. 내 정보 수정

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 내 정보 수정 API |
| 설명 | 로그인한 사용자가 본인의 부서, 휴대폰 번호를 부분 수정한다. (REQ-USER-007) |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |
| 담당 | 박유정 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer `<access_token>` | 로그인 사용자 확인 |
| Content-Type | application/json | JSON 본문 전송 |

**본문 필드** (보낸 항목만 수정)

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| department | string | N | `developer` / `medical team` / `researcher` |
| phone_number | string | N | 하이픈 없는 휴대폰 번호 (다른 회원과 중복 불가) |

```json
{ "department": "researcher", "phone_number": "01098765432" }
```

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: 수정된 회원 정보 (`UserResponse`)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 400 | `{"detail": "수정할 항목을 하나 이상 입력해주세요."}` | 본문이 비었거나 값이 모두 null |
| 409 | `{"detail": "이미 사용 중인 휴대폰 번호입니다."}` | 다른 회원의 번호 |
| 401 / 403 | 1-5 참고 | 인증 실패 |
| 422 | 1-5 참고 | 형식 오류 |

#### 4) 비고

- 수정 가능한 항목은 부서, 휴대폰 번호뿐이다. 요청 스키마에 다른 항목을 넣지 않는다.
- Day02 PR #9에서 배운 대로 `model_dump(exclude_none=True)`로 입력값만 꺼낸다.

---

### API 7. 비밀번호 변경

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 비밀번호 변경 API |
| 설명 | 기존 비밀번호를 확인한 뒤 새 비밀번호로 변경한다. (REQ-USER-008) |
| 엔드포인트 | `/api/v1/users/me/password` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |
| 담당 | 이명석 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer `<access_token>` | 로그인 사용자 확인 |
| Content-Type | application/json | JSON 본문 전송 |

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| current_password | string | Y | 기존 비밀번호 |
| new_password | string | Y | 새 비밀번호 (8-20자, 대문자·특수문자 포함) |

```json
{ "current_password": "Abcdefg1!", "new_password": "Newpass1!" }
```

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK** (`MessageResponse`)

```json
{ "message": "비밀번호가 변경되었습니다." }
```

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 400 | `{"detail": "기존 비밀번호가 일치하지 않습니다."}` | 기존 비밀번호 틀림 |
| 400 | `{"detail": "새 비밀번호가 기존 비밀번호와 같습니다."}` | 같은 비밀번호로 변경 |
| 401 / 403 | 1-5 참고 | 인증 실패 |
| 422 | 1-5 참고 | 새 비밀번호 규칙 위반 |

#### 4) 비고

- `verify_password(current_password, user.hashed_password)`로 확인하고 `hash_password(new_password)`로 저장한다.
- 처음에는 `old_password`로 설계했으나, 통합 테스트에서 프론트(`static/pages.js`)가 `current_password`로 보내 422가 나는 것을 확인해 프론트에 맞춰 수정했다.

---

### API 8. 회원 탈퇴

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원탈퇴 API |
| 설명 | 로그인한 사용자가 마이페이지에서 본인의 계정을 탈퇴한다. (REQ-USER-009) |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y |
| 담당 | 박유정 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer `<access_token>` | 탈퇴할 현재 로그인 사용자 확인 |

**본문 필드**: 없음
**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 204 No Content**: 본문 없음

**응답 Headers**

| Key | 예시 값 | 설명 |
|---|---|---|
| Set-Cookie | `refresh_token=""; Max-Age=0; Path=/api/v1/users` | 리프레시 토큰 쿠키 삭제 (`delete_refresh_cookie`) |

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 / 403 | 1-5 참고 | 인증 실패 |

#### 4) 비고 (요구사항과 다르게 결정, 3번 참고)

- 행을 지우지 않고 삭제 표시한다: `is_deleted = True`, `deleted_at = 현재 시각`, `is_active = False`
- 개인정보는 즉시 지운다: 이메일·휴대폰 번호·이름을 식별할 수 없는 값으로 바꾸고 비밀번호 해시도 지운다
  - 예: `email = deleted_<id>@deleted.local`, `phone_number = deleted_<id>`, `name = 탈퇴회원`
- 탈퇴 후 같은 토큰으로 요청하면 401 (`CurrentUser`가 탈퇴 회원을 제외함)

---

### API 9. 회원 목록 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 목록 조회 API |
| 설명 | 어드민이 회원관리 메뉴에서 전체 회원을 검색·필터링해 조회한다. (REQ-USER-004) |
| 엔드포인트 | `/api/v1/admin/users` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (어드민) |
| 담당 | 이명석 (목록 조회), 김지연 (검색 조건 query·department) |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer `<access_token>` | 어드민 확인 |

**본문 필드**: 없음

**쿼리 파라미터** (Query Parameter Model 사용)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| query | string | N | 이메일 또는 이름에 포함된 문자열로 검색 |
| department | string | N | `developer` / `medical team` / `researcher` |

예: `GET /api/v1/admin/users?query=김&department=medical%20team`

#### 3) 응답 (Response)

**성공 · 200 OK**: 회원 정보 배열 (`list[UserResponse]`)

```json
[
  { "id": 1, "email": "doctor@example.com", "name": "김의사", "department": "medical team", "gender": "female", "phone_number": "01012345678", "role": "staff", "is_active": true }
]
```

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | 1-5 참고 | 인증 실패 |
| 403 | `{"detail": "관리자 권한이 필요합니다."}` | 어드민 아님 |
| 422 | 1-5 참고 | department 값 오류 |

#### 4) 비고

- 탈퇴 회원(`is_deleted = true`)은 목록에서 제외한다.

---

### API 10. 회원 권한 변경

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 권한 변경 API |
| 설명 | 어드민이 선택한 회원의 권한을 변경한다. (REQ-USER-005) |
| 엔드포인트 | `/api/v1/admin/users/role` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y (어드민) |
| 담당 | 이명석 |

#### 2) 요청 (Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | Bearer `<access_token>` | 어드민 확인 |
| Content-Type | application/json | JSON 본문 전송 |

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| user_id | integer | Y | 권한을 바꿀 회원 ID |
| new_role | string | Y | `pending` / `staff` / `admin` |

```json
{ "user_id": 2, "new_role": "staff" }
```

**쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: 변경된 회원 정보 (`UserResponse`)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 400 | `{"detail": "본인의 권한은 변경할 수 없습니다."}` | 자기 자신 변경 |
| 401 | 1-5 참고 | 인증 실패 |
| 403 | `{"detail": "관리자 권한이 필요합니다."}` | 어드민 아님 |
| 404 | `{"detail": "회원을 찾을 수 없습니다."}` | 없는 회원, 탈퇴 회원 |
| 422 | 1-5 참고 | new_role 값 오류 |

#### 4) 비고

- 본인 권한 변경을 막는 이유: 마지막 어드민이 실수로 권한을 내리면 관리자가 사라진다.

---

## 3. 요구사항과 다르게 결정한 부분

### 회원 탈퇴: 즉시 삭제 대신 삭제 표시 + 개인정보 삭제

- **요구사항**: REQ-USER-009 "회원탈퇴 시 Database에서 회원과 관련된 정보는 모두 즉시 삭제한다."
- **결정**: 행을 지우지 않고 삭제 표시(Soft Delete)를 하되, **개인정보는 즉시 지운다.** (팀 논의 10/26)
- **이유**
  1. Day03에 팀이 의료 기록 보존을 위해 모든 테이블을 Soft Delete로 결정했다.
  2. `xray_images.uploader_id`가 `RESTRICT`라, 이미지를 업로드한 회원은 DB가 실제 삭제를 막는다. 행을 지우면 "누가 이 X-ray를 올렸는가"라는 의료 기록의 출처도 사라진다.
  3. 대신 이메일·휴대폰 번호·이름·비밀번호를 지워 요구사항의 취지(회원 정보 즉시 삭제)를 지킨다. 이메일·휴대폰 번호가 비워지므로 같은 정보로 재가입도 가능하다.

## 4. 코드 구조와 분담

```
app/
├── core/
│   ├── config.py          # JWT 설정 (SECRET_KEY, 만료 시간)
│   ├── security.py        # 비밀번호 해싱(Argon2), JWT 발급·검증, Refresh 쿠키
│   └── dependencies.py    # CurrentUser, StaffUser, AdminUser
├── schemas/users.py       # 요청·응답 Pydantic 모델, 입력값 검증
├── repositories/users.py  # DB 조회·저장
├── services/users.py      # 비즈니스 로직
└── apis/
    ├── users.py           # /api/v1/users
    └── admin.py           # /api/v1/admin
```

| 담당 | API |
|---|---|
| 김지연 | 공통 뼈대(설정, 보안, 의존성, 쿠키, 응답 스키마, 라우터 등록) + 회원가입 + 토큰 재발급 + 회원 목록 검색 조건 |
| 김도엽 | 로그인 + 로그아웃 |
| 박유정 | 내 정보 조회 + 수정 + 회원 탈퇴 |
| 이명석 | 비밀번호 변경 + 회원 목록 + 권한 변경 |

- 김지연이 공통 뼈대와 회원가입을 먼저 merge한다. 토큰 재발급은 뼈대 merge 후 다른 팀원과 같은 방식으로 PR을 올린다.
- 팀원은 각 파일의 `# ===== [이름] ... =====` 주석 아래에만 작성해 충돌을 줄인다.
- 작성 순서: **schemas → repositories → services → apis** (Day03 뜯어보기 5번)
- 로그인·토큰 재발급·로그아웃·탈퇴는 같은 쿠키를 다루므로 반드시 공통 쿠키 함수를 쓴다.

## 📚 참고 자료

- [FastAPI 요청 본문 (Pydantic BaseModel)](https://fastapi.tiangolo.com/ko/tutorial/body/#import-pydantics-basemodel)
- [FastAPI 쿼리 매개변수 모델](https://fastapi.tiangolo.com/ko/tutorial/query-param-models/)
- [Pydantic AfterValidator](https://pydantic.dev/docs/validation/latest/api/pydantic/functional_validators/#pydantic.functional_validators.AfterValidator)
- [FastAPI JWT 인증 - suwani](https://suwani.tistory.com/188)
- [FastAPI Argon2 비밀번호 해싱 - chaechae](https://chaechae.life/blog/fastapi-password-hasing-with-agron2)
