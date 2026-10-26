# 📝 Day04 작업 내역

- 날짜: 2026-10-26
- PR: #22 ~ #30
- 작업자: 김지연, 김도엽, 박유정, 이명석

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 9개 | 설계 문서, 보안·의존성 공통 코드, 스키마·repository·service·api, 로그인 테스트 코드, 작업 내역 |
| ✏️ 수정한 것 | 5개 | config, main, .env.example, pyproject.toml·uv.lock, README |
| 🔌 완성한 API | 10개 | 회원가입, 로그인, 토큰 재발급, 로그아웃, 내 정보 조회·수정, 비밀번호 변경, 회원 탈퇴, 회원 목록, 권한 변경 |
| 🐛 통합 테스트에서 고친 것 | 2개 | 비밀번호 변경 필드 이름, 탈퇴 직후 로그아웃 반복 |

| PR | 내용 | 담당 |
|---|---|---|
| #22 | 인증 뼈대 + User API 설계 + 회원가입 | 김지연 |
| #23 | 토큰 재발급 | 김지연 |
| #24 | 로그인 / 로그아웃 (+ pytest 테스트 코드) | 김도엽 |
| #25 | 내 정보 조회 / 수정 / 회원 탈퇴 | 박유정 |
| #26 | 비밀번호 변경 / 회원 목록 / 권한 변경 (첫 버전, #27로 대체되어 닫음) | 이명석 |
| #27 | 비밀번호 변경 / 회원 목록 / 권한 변경 | 이명석 |
| #28 | 회원 목록 검색 조건 + User API 코드 정리 | 김지연 |
| #29 | 비밀번호 변경 요청 필드를 프론트에 맞춤 | 김지연 |
| #30 | 로그아웃 API 로그인 확인 제거 | 김지연 |

## 🆕 새로 만든 것

### `docs/day04_USER_API_설계.md` - User API 설계 (과제 1)

- **왜**: 과제 1. 요구사항 정의서를 바탕으로 API 명세를 작성한다.
- **어떻게**: 과제에서 준 API 명세서 예시 형식(개요 → 요청 Headers·본문·쿼리 → 응답 성공·실패와 필드 표 → 비고)에 맞춰 API 10개를 정리했다. 주소와 요청 형식은 프론트(`static/apis.js`)가 이미 호출하는 형식에 맞췄다. 회원 탈퇴는 Day03 결정(Soft Delete)에 따라 요구사항과 다르게 설계하고 이유를 남겼다.
- 통합 테스트에서 설계와 프론트가 다른 부분 2곳을 찾아 문서도 같이 고쳤다 (비밀번호 변경 필드 이름, 로그아웃 인증 여부). 고친 이유는 각 API의 비고에 남겼다.

### `app/core/security.py` - 비밀번호 해싱, JWT

- **왜**: 비밀번호를 평문으로 저장하지 않고, 로그인 후 JWT로 인가해야 한다(NFR-USER-001).
- **어떻게**
  - `pwdlib`의 Argon2로 `hash_password`, `verify_password`
  - `pyjwt`로 Access(30분)·Refresh(7일) 토큰 발급. 페이로드는 `sub`(user_id), `type`, `exp`
  - `decode_token`은 서명 오류·만료·종류 불일치를 모두 `None`으로 돌려준다
  - Refresh Token 쿠키 공통 함수 `set_refresh_cookie`, `delete_refresh_cookie`. 로그인·재발급·로그아웃 담당이 달라도 쿠키 이름과 `path`가 어긋나지 않도록 한 곳에서 관리

### `app/core/dependencies.py` - 인증·권한 의존성

- **왜**: 로그인이 필요한 API마다 토큰 검증을 반복하지 않도록 공통으로 만들었다.
- **어떻게**
  - `CurrentUser`: Bearer 토큰 검증 → 회원 조회. 토큰 오류·탈퇴 회원은 401, 비활성 회원은 403 (과제 API 명세서 예시와 맞춤)
  - `StaffUser`: 대기자(`pending`)면 403
  - `AdminUser`: 어드민이 아니면 403
  - `OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")`로 Swagger의 Authorize 버튼과 연결

### `app/schemas/users.py`, `repositories/users.py`, `services/users.py`, `apis/users.py`, `apis/admin.py`

- **왜**: Day03에 정리한 계층 구조(apis → services → repositories → models)를 실제로 적용한다.
- **어떻게**
  - 공통 검증 타입(이메일, 비밀번호, 이름, 휴대폰 번호)과 공통 응답 스키마 `UserResponse`, `TokenResponse`(로그인·재발급 공용, `access_token`·`token_type`·`expires_in`), `MessageResponse`
  - repository는 탈퇴 회원을 조회에서 제외. 단, 중복 확인은 탈퇴 회원까지 포함 (unique 제약이 걸려 있으므로)
  - **회원가입** 구현: 이메일·휴대폰 번호 중복 409, 비밀번호 Argon2 해싱, 권한 기본값 `pending`
  - 팀원 담당 위치를 `# ===== [이름] ... =====` 주석으로 나눠둠

### `tests/test_user_login_logout.py` - 로그인 테스트 (김도엽)

- **왜**: 로그인 실패 경우(없는 이메일, 틀린 비밀번호, 비활성 회원)를 매번 Swagger로 확인하지 않도록 자동 테스트로 만들었다.
- **어떻게**: DB 대신 `AsyncMock`으로 repository를 바꿔 끼워 service만 테스트한다. `pytest`, `pytest-asyncio`를 dev 의존성으로 추가하고, `pyproject.toml`에 `pythonpath = ["."]`를 넣어 `uv run pytest`로 실행된다.

## ✏️ 수정한 것

| 파일 | 왜 / 어떻게 |
|---|---|
| `app/core/config.py` | JWT 설정 추가 (`SECRET_KEY`, `JWT_ALGORITHM`, 만료 시간) |
| `.env.example` | `SECRET_KEY` 항목 추가. 실제 값은 각자 `.env`에 넣는다 |
| `app/main.py` | `user_router`, `admin_router` 등록 (`catch_all`보다 위) |
| `pyproject.toml`, `uv.lock` | `uv add "pwdlib[argon2]" pyjwt`, dev 의존성 `pytest`. **팀원 전원 `uv sync` 필요** |
| `README.md` | 문서 표를 📚 과제 문서 / 📝 작업 내역으로 나누고 날짜 칸 추가 |

## 💬 공통 설계 결정

- 세 API가 같은 쿠키를 다루므로 쿠키 함수와 `TokenResponse`를 뼈대에 공통으로 넣었다.
- 과제 명세서 예시에 맞춰 `TokenResponse`에 `expires_in`(1800초)을 추가했다. 예시의 `user` 정보는 프론트가 `/users/me`로 따로 받아오므로 넣지 않았다.

## ✅ 확인한 것 - 뼈대 (Docker MySQL)

| 테스트 | 결과 |
|---|---|
| 정상 회원가입 | 201, 권한 `pending`, 응답에 비밀번호 없음 |
| 이메일 중복 / 휴대폰 번호 중복 | 409 / 409 |
| 이메일·비밀번호·이름·휴대폰·부서·성별 형식 위반 | 모두 422 |
| DB 저장값 | 비밀번호가 `$argon2id$...`로 해싱되어 저장, `verify_password` 통과 |
| Access / Refresh 토큰 구분 | Refresh Token을 Access 자리에 넣으면 거부 |
| 토큰 없음 / 위조 토큰 | 401 / 401 |
| 대기자로 스태프·어드민 전용 접근 | 403 / 403 |
| 어드민으로 변경 후 | 200 / 200 |
| 탈퇴 표시된 회원의 토큰 | 401 |
| 비활성(`is_active = false`) 회원의 토큰 | 403 |

## 🔄 토큰 재발급 API (김지연)

### `app/services/users.py` - `refresh_access_token`

- **왜**: Access Token(30분)이 만료되면 사용자가 다시 로그인하지 않고도 계속 쓸 수 있어야 한다(NFR-USER-001).
- **어떻게**
  1. 쿠키의 Refresh Token을 `decode_token(..., REFRESH_TOKEN_TYPE)`으로 검증. 없음·만료·위조·종류 불일치면 401
  2. `get_user_by_id`로 회원 조회. 탈퇴 회원은 조회되지 않아 401
  3. 비활성 회원이면 403
  4. `create_access_token`으로 새 Access Token 발급

### `app/apis/users.py` - `POST /api/v1/users/refresh`

- `request.cookies.get(REFRESH_COOKIE_NAME)`으로 쿠키를 읽어 service에 넘기고 `TokenResponse`로 응답한다.

### 작성하면서 배운 것

- `status.HTTP_401_CONFLICT`처럼 **숫자와 이름이 짝이 안 맞는 상태 코드**는 존재하지 않아 `AttributeError`가 난다. 정상 요청에서는 그 줄까지 가지 않아 에러가 안 보이고, **실패하는 경우를 테스트해야** 드러난다.
- 상태 코드 짝: 401 `UNAUTHORIZED`(누군지 모름), 403 `FORBIDDEN`(누군지는 알지만 안 됨), 409 `CONFLICT`(중복)

### 확인한 것

| 테스트 | 결과 |
|---|---|
| 정상 쿠키 | 200, 새 Access Token (`expires_in` 1800) |
| 쿠키 없음 / 위조 쿠키 | 401 / 401 |
| Access Token을 쿠키에 넣음 | 401 (토큰 종류 구분) |
| 비활성 회원 / 탈퇴 회원 | 403 / 401 |

## 👥 팀원 API

### 로그인 / 로그아웃 (김도엽, PR #24)

- **로그인** `POST /users/login`: `OAuth2PasswordRequestForm`으로 받아 Swagger Authorize 버튼과 바로 연결된다. `username` 칸에 이메일을 넣는다(OAuth2 규격이라 칸 이름이 고정). 없는 이메일과 틀린 비밀번호를 **같은 401 문구**로 묶어 가입 여부가 드러나지 않게 했다. 성공하면 Access Token은 본문으로, Refresh Token은 공통 쿠키 함수로 내려준다.
- **로그아웃** `POST /users/logout`: `delete_refresh_cookie`로 쿠키를 지운다.
- 리뷰: 섹션 주석 끝 `\n` 문자, `uv run pytest`에서 `No module named 'app'` 에러를 Request changes로 남겼고, 수정 후 merge했다.

### 내 정보 조회 / 수정 / 회원 탈퇴 (박유정, PR #25)

- **조회** `GET /users/me`, **수정** `PATCH /users/me`: 부서와 휴대폰 번호만 수정할 수 있다. 빈 요청 400, 다른 회원의 번호면 409, 번호를 그대로 보내면 중복 검사를 건너뛴다.
- **탈퇴** `DELETE /users/me`: 설계대로 Soft Delete + 개인정보 삭제. 이메일·번호를 `deleted_{id}`로 바꿔 **같은 정보로 재가입**할 수 있고, Refresh Token 쿠키도 지운다.
- 리뷰: 가입 → 조회 → 수정 → 탈퇴 → 재가입까지 테스트해 Approve했다. 줄 간격 정리는 #28에서 한 번에 했다.

### 비밀번호 변경 / 회원 목록 / 권한 변경 (이명석, PR #26 → #27)

- **비밀번호 변경** `PATCH /users/me/password`: 기존 비밀번호 확인 400, 같은 비밀번호 400, 규칙 위반 422
- **회원 목록** `GET /admin/users`: 탈퇴 회원 제외, 어드민만 접근
- **권한 변경** `PATCH /admin/users/role`: 본인 권한 변경 400, 없는 회원 404, 없는 권한 값 422
- #26에서 회원 목록과 권한 변경이 500 에러가 나서 같이 원인을 찾았다.

| 원인 | 설명 | 수정 |
|---|---|---|
| `Depends(AdminUser)` | `AdminUser`는 이미 `Annotated[User, Depends(...)]`라 한 번 더 감싸면 관리자 확인을 건너뛰고 `args`, `kwargs` 칸을 요구한다 | `admin: AdminUser`처럼 타입 자리에 바로 사용 |
| `user_service.get_user_by_id` | services에 없는 함수라 `AttributeError` | repository의 `get_user_by_id`로 조회, 없으면 404 |
| 쿼리로 받음 | 설계와 프론트는 JSON 본문으로 보낸다 | `ChangePasswordRequest`, `ChangeUserRoleRequest` 사용 |
| 비밀번호 검사 없음 | 새 비밀번호를 `1`로 보내도 바뀌었다 (500은 아니지만 보안 문제) | 기존 비밀번호 확인, 규칙 검사 추가 |
| `return` 누락 | 수정본에서 권한 변경이 회원을 찾고 `None`을 돌려줘 여전히 500 | 마지막에 `return await user_repository.update_user_role(...)` |

- #26은 유정님 PR 이전 develop 기준이라 충돌이 나서, develop 위에서 새로 만든 **#27을 merge하고 #26은 닫았다.**

## 🔍 회원 목록 검색 조건 + 코드 정리 (김지연, PR #28)

### 검색 조건 `GET /admin/users?query=김&department=medical%20team`

- **왜**: 설계 문서와 프론트 회원 관리 화면(검색창, 부서 선택)에 이미 있는 기능인데 서버가 조건을 무시하고 전체 목록만 주고 있었다.
- **어떻게**
  - `schemas`: 쿼리 파라미터 모델 `UserListQuery` (`query`, `department` 모두 선택)
  - `apis/admin.py`: `params: Annotated[UserListQuery, Query()]`로 받음 (과제 참고 링크의 FastAPI 쿼리 매개변수 모델)
  - `repositories`: 값이 있을 때만 조건을 붙인다. `query`는 이메일 또는 이름에 포함(`or_`, `contains`), `department`는 일치. id 순 정렬

### 코드 정리 (동작 변경 없음)

- 파일 중간에 있던 import를 맨 위로 옮겼다 (`apis/admin.py`, `apis/users.py`, `repositories/users.py`, `services/users.py`)
- 함수·섹션 사이 빈 줄 2줄로 통일, 파일 끝 줄바꿈 추가
- 기능(`feat`)과 정리(`style`)는 커밋을 나눴다

## 🖥️ 통합 테스트 (프론트 화면 `/`, Swagger `/docs`)

User API 10개가 develop에 모인 뒤, 템플릿 프론트에서 실제 사용자 흐름대로 테스트했다.

| 화면 | 테스트 | 결과 |
|---|---|---|
| Swagger | 로그인 → 토큰 재발급 → Authorize → 로그아웃 → 재발급 | 200 → 200(새 토큰) → 200 → 401 |
| 회원가입 | 가입 후 로그인 | 대기자라 "관리자의 승인을 기다리는 중입니다." 화면 |
| 회원 관리 | 전체 목록 | 탈퇴 회원(ID 8) 제외 확인 |
| 회원 관리 | 이름 검색, 이메일 검색 | 해당 회원만 표시 |
| 회원 관리 | 부서 필터(의료진), 검색어 + 부서 | 조건에 맞는 회원만 표시 |
| 회원 관리 | 권한 변경, 내 계정 권한 | 변경 반영 / 내 계정은 드롭다운 잠김 |
| 마이페이지 | 부서 수정 | 상단 표시까지 반영 |
| 마이페이지 | 비밀번호 변경 → 새 비밀번호로 재로그인 | 성공 (#29 수정 후) |
| 마이페이지 | 회원 탈퇴 | DB에 `is_deleted = True`, 이메일 `deleted_7@deleted.local` |

### 통합 테스트에서 발견해 고친 것

**1. 비밀번호 변경 "필수 입력 항목입니다." (PR #29)**

- 원인: 프론트(`static/pages.js`)는 `current_password`로 보내는데 백엔드는 `old_password`를 기다려 422가 났다. 설계 문서에 `old_password`로 적은 것이 원인이었다.
- 수정: 스키마·서비스·설계 문서를 `current_password`로 바꿨다. 템플릿 프론트는 그대로 두고 백엔드를 맞췄다.
- 다른 API의 요청 필드(`user_id`·`new_role`, `department`·`phone_number`)도 프론트와 맞는지 함께 확인했다.

**2. 회원 탈퇴 후 화면이 멈춤 (PR #30)**

- 원인: 탈퇴 후 프론트가 로그아웃을 부르는데, 로그아웃이 로그인 확인(`CurrentUser`)을 요구해 탈퇴한 회원은 401 → 프론트가 토큰 재발급 시도 → 쿠키가 이미 없어 실패 → 다시 로그아웃을 **무한 반복**했다.
- 수정: 로그아웃은 내 브라우저 쿠키만 지우는 동작이라 인증 없이도 안전하므로 로그인 확인을 뺐다. Access Token이 만료된 상태에서도 로그아웃이 된다. 설계 문서 API 4의 인증 여부를 N으로 고쳤다.
- #24 리뷰 때 "토큰이 안 통하면 로그아웃을 못 한다"고 남겼던 우려가 실제로 드러난 경우였다.

| 테스트 | 결과 |
|---|---|
| 정상 로그아웃 / 로그아웃 후 재발급 | 200 / 401 |
| 토큰 없이 / 깨진 토큰으로 로그아웃 | 200 / 200 |
| 탈퇴 직후 로그아웃 | 200 (수정 전에는 401 반복) |

### 발견했지만 그대로 둔 것 (템플릿 프론트 동작)

- 대기자(`pending`)는 프론트가 홈 외의 페이지를 모두 막아서 **마이페이지에도 못 들어간다.** 설계와 API는 대기자도 마이페이지를 쓸 수 있게 되어 있다. 프론트 `static/app.js`의 `publicPaths`에 `/my-page`를 넣을지는 팀과 논의가 필요하다.
- 비밀번호 변경이 400이면 프론트가 우리 메시지("기존 비밀번호가 일치하지 않습니다.") 대신 고정 문구를 보여준다.
- admin으로 로그인하면 환자 관리(`/patients`)로 이동해 "Not Found"가 뜬다. 환자 API는 다음 Stage 범위다.
- 회원 관리 표의 상태 칸(`활성`)이 좁아 두 줄로 깨진다 (CSS).

## 💡 배운 것

- `Annotated`로 만든 의존성(`CurrentUser`, `AdminUser`)은 **타입 자리에 바로 쓴다.** `Depends()`로 한 번 더 감싸면 엉뚱한 파라미터를 요구한다.
- 함수가 `return`을 빠뜨리면 `None`이 돌아가서, 그다음 줄(`model_validate`)에서 500이 난다.
- 우리 파이썬은 3.14라 import를 빠뜨린 타입 힌트도 우연히 돌아갔지만, 프로젝트 설정은 `>=3.13`이라 **3.13 쓰는 팀원 컴퓨터에서는 서버가 안 켜진다.** 내 컴퓨터에서 된다고 끝이 아니다.
- **설계 문서만 보고 만들면 프론트와 어긋날 수 있다.** API 주소(`apis.js`)뿐 아니라 실제로 보내는 데이터(`pages.js`)까지 확인해야 한다. Swagger 테스트로는 잡히지 않았고 **프론트 통합 테스트에서만** 드러났다.
- PR을 올리기 전에 최신 develop을 merge하면 충돌을 미리 풀 수 있다 (#26 → #27).
- 파일 끝에 줄바꿈이 없으면 다음 사람이 아래에 코드를 추가할 때 원래 마지막 줄까지 바뀐 것처럼 diff에 나온다.

## ⏭️ 남은 작업

- [x] 뼈대 PR 리뷰·merge 후 팀원 `uv sync`, `.env`에 `SECRET_KEY` 추가 공지
- [x] 김지연: 토큰 재발급
- [x] 김도엽: 로그인, 로그아웃
- [x] 박유정: 내 정보 조회, 수정, 탈퇴
- [x] 이명석: 비밀번호 변경, 회원 목록, 권한 변경
- [x] 김지연: 회원 목록 검색 조건, 코드 정리
- [x] Swagger + 프론트 통합 테스트
- [x] 로그아웃 수정 PR #30 merge
- [ ] 로컬 테스트 계정 정리
- [ ] 대기자 마이페이지 접근(프론트 `publicPaths`) 팀 논의
- [ ] develop → main
