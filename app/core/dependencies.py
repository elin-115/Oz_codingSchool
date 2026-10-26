from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.enums import UserRole
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models import User
from app.repositories import users as user_repository

# Swagger의 Authorize 버튼이 로그인 API로 토큰을 받아오도록 tokenUrl 지정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

DBSession = Annotated[AsyncSession, Depends(async_get_db)]


async def get_current_user(
    db: DBSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    # Authorization: Bearer <access_token> 헤더의 토큰으로 로그인한 회원을 찾음
    user_id = decode_token(token, ACCESS_TOKEN_TYPE)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 탈퇴했거나 없는 회원은 401, 비활성화된 회원은 403으로 구분
    user = await user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 회원입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 사용자입니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_staff_user(user: CurrentUser) -> User:
    # 대기자(PENDING)는 마이페이지 외 서비스에 접근할 수 없음
    if user.role == UserRole.PENDING:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 승인 후 이용할 수 있습니다.")
    return user


async def get_admin_user(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return user


StaffUser = Annotated[User, Depends(get_staff_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
