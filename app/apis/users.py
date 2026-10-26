from fastapi import APIRouter, Request, status

from app.core.dependencies import DBSession
from app.core.security import REFRESH_COOKIE_NAME
from app.schemas.users import SignupRequest, TokenResponse, UserResponse
from app.services import users as user_service

user_router = APIRouter(prefix="/api/v1/users", tags=["Users"])


# ===== [김지연] 회원가입 =====
@user_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest, db: DBSession) -> UserResponse:
    user = await user_service.signup(db, data)
    return UserResponse.model_validate(user)


# ===== [김도엽] 로그인 POST /login · 로그아웃 POST /logout =====
# 쿠키는 app.core.security의 set_refresh_cookie / delete_refresh_cookie 사용


# ===== [김지연] 토큰 재발급 POST /refresh =====
@user_router.post("/refresh")
async def refresh(request: Request, db: DBSession) -> TokenResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    access_token = await user_service.refresh_access_token(db, refresh_token)
    return TokenResponse(access_token=access_token)

# ===== [박유정] 내 정보 조회 GET /me · 수정 PATCH /me · 탈퇴 DELETE /me =====


# ===== [이명석] 비밀번호 변경 PATCH /me/password =====
