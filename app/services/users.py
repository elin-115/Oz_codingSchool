from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User
from app.repositories import users as user_repository
from app.schemas.users import SignupRequest

# 비즈니스 규칙(중복 확인, 해싱, 권한 등)을 담당하고 DB 작업은 repository에 맡긴다.


# ===== [김지연] 회원가입 =====

async def signup(db: AsyncSession, data: SignupRequest) -> User:
    if await user_repository.exists_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
    if await user_repository.exists_phone_number(db, data.phone_number):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 휴대폰 번호입니다.")

    # 비밀번호는 Argon2로 해싱해서 저장, 권한은 기본값 PENDING(대기자)
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        name=data.name,
        department=data.department,
        gender=data.gender,
        phone_number=data.phone_number,
    )
    return await user_repository.create_user(db, user)


# ===== [김도엽] 로그인 / 토큰 재발급 / 로그아웃 =====


# ===== [박유정] 내 정보 조회 / 수정 / 탈퇴 =====


# ===== [이명석] 비밀번호 변경 / 회원 목록 / 권한 변경 =====
