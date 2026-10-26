from fastapi import APIRouter

admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ===== [이명석] 회원 목록 조회 GET /users · 권한 변경 PATCH /users/role =====
# 관리자만 접근 가능: app.core.dependencies의 AdminUser 사용
from app.core.dependencies import AdminUser, DBSession
from app.schemas.users import ChangeUserRoleRequest, UserResponse
from app.services import users as user_service


@admin_router.get("/users")
async def get_user_list(db: DBSession, admin: AdminUser) -> list[UserResponse]:
    users = await user_service.get_user_list(db)
    return [UserResponse.model_validate(user) for user in users]


@admin_router.patch("/users/role")
async def change_user_role(data: ChangeUserRoleRequest, db: DBSession, admin: AdminUser) -> UserResponse:
    user = await user_service.change_user_role(db, admin, data)
    return UserResponse.model_validate(user)