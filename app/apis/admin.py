from fastapi import APIRouter

admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ===== [이명석] 회원 목록 조회 GET /users · 권한 변경 PATCH /users/role =====
# 관리자만 접근 가능: app.core.dependencies의 AdminUser 사용
from fastapi import Depends
from app.core.dependencies import DBSession, AdminUser
from app.schemas.users import UserResponse
from app.services import users as user_service
from fastapi import status

# 회원 목록 조회
# 모든 회원 조회
# 목록 조회 시 검색 기능을 활용하여 이메일 혹은 이름으로 검색을 할 수 있다.
@admin_router.get("/users", status_code=status.HTTP_200_OK)
async def get_user_list(db: DBSession, current_user=Depends(AdminUser)) -> list[UserResponse]:
    users = await user_service.get_user_list(db)
    return [UserResponse.model_validate(user) for user in users]


#권한 변경
@admin_router.patch("/users/role", status_code=status.HTTP_200_OK)
async def change_user_role(user_id: int, new_role: str, db: DBSession, current_user=Depends(AdminUser)) -> UserResponse:
    user = await user_service.change_user_role(db, await user_service.get_user_by_id(db, user_id), new_role)
    return UserResponse.model_validate(user)