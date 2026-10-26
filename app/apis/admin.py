from fastapi import APIRouter

admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ===== [이명석] 회원 목록 조회 GET /users · 권한 변경 PATCH /users/role =====
# 관리자만 접근 가능: app.core.dependencies의 AdminUser 사용
