# 📝 Day04 작업 내역

- 날짜: 2026-10-26
- 브랜치: `feature/user-api-base_261026`
- 작업자: 김지연

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 8개 | 설계 문서, 보안·의존성 공통 코드, 스키마·repository·service·api, 작업 내역 |
| ✏️ 수정한 것 | 5개 | config, main, .env.example, pyproject.toml·uv.lock, README |

## 🆕 새로 만든 것

### `docs/day04_USER_API_설계.md` - User API 설계 (과제 1)

- **왜**: 과제 1. 요구사항 정의서를 바탕으로 API 명세를 작성한다.
- **어떻게**: API 10개의 Method·Endpoint·권한·요청·응답·에러를 정리했다. 주소와 요청 형식은 프론트(`static/apis.js`)가 이미 호출하는 형식에 맞췄다. 회원 탈퇴는 Day03 결정(Soft Delete)에 따라 요구사항과 다르게 설계하고 이유를 남겼다.

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
  - `CurrentUser`: Bearer 토큰 검증 → 회원 조회. 탈퇴·비활성 회원은 401
  - `StaffUser`: 대기자(`pending`)면 403
  - `AdminUser`: 어드민이 아니면 403
  - `OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")`로 Swagger의 Authorize 버튼과 연결

### `app/schemas/users.py`, `repositories/users.py`, `services/users.py`, `apis/users.py`, `apis/admin.py`

- **왜**: Day03에 정리한 계층 구조(apis → services → repositories → models)를 실제로 적용한다.
- **어떻게**
  - 공통 검증 타입(이메일, 비밀번호, 이름, 휴대폰 번호)과 공통 응답 스키마 `UserResponse`, `TokenResponse`(로그인·재발급 공용), `MessageResponse`
  - repository는 탈퇴 회원을 조회에서 제외. 단, 중복 확인은 탈퇴 회원까지 포함 (unique 제약이 걸려 있으므로)
  - **회원가입** 구현: 이메일·휴대폰 번호 중복 409, 비밀번호 Argon2 해싱, 권한 기본값 `pending`
  - 팀원 담당 위치를 `# ===== [이름] ... =====` 주석으로 나눠둠

## ✏️ 수정한 것

| 파일 | 왜 / 어떻게 |
|---|---|
| `app/core/config.py` | JWT 설정 추가 (`SECRET_KEY`, `JWT_ALGORITHM`, 만료 시간) |
| `.env.example` | `SECRET_KEY` 항목 추가. 실제 값은 각자 `.env`에 넣는다 |
| `app/main.py` | `user_router`, `admin_router` 등록 (`catch_all`보다 위) |
| `pyproject.toml`, `uv.lock` | `uv add "pwdlib[argon2]" pyjwt`. **팀원 전원 `uv sync` 필요** |
| `README.md` | 문서 표에 Day04 추가 |

## 💬 분담 변경

- 처음에는 김도엽이 로그인·토큰 재발급·로그아웃 3개를 맡았지만, 쿠키와 토큰을 함께 다뤄 부담이 커서 **토큰 재발급을 김지연이 가져왔다.**
- 세 API가 같은 쿠키를 다루므로 쿠키 함수와 `TokenResponse`를 뼈대에 공통으로 넣었다.

## ✅ 확인한 것 (Docker MySQL)

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

## ⏭️ 남은 작업

- [ ] 뼈대 PR 리뷰·merge 후 팀원 `uv sync`, `.env`에 `SECRET_KEY` 추가 공지
- [ ] 김지연: 토큰 재발급
- [ ] 김도엽: 로그인, 로그아웃
- [ ] 박유정: 내 정보 조회, 수정, 탈퇴
- [ ] 이명석: 비밀번호 변경, 회원 목록, 권한 변경
- [ ] Swagger 통합 테스트 → develop → main
