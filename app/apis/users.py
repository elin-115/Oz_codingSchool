from fastapi import APIRouter, status

from app.core.dependencies import DBSession
from app.schemas.users import SignupRequest, UserResponse
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


# ===== [박유정] 내 정보 조회 GET /me · 수정 PATCH /me · 탈퇴 DELETE /me =====


# ===== [이명석] 비밀번호 변경 PATCH /me/password =====
