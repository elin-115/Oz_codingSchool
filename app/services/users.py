from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
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


# ===== [김도엽] 로그인 / 로그아웃 =====
async def login(
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[str, str]:
    """이메일과 비밀번호를 검증하고 Access/Refresh Token을 발급한다."""
    user = await user_repository.get_user_by_email(db, email)

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 일치하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 사용자입니다.",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return access_token, refresh_token




# ===== [김지연] 토큰 재발급 =====
# 쿠키에서 꺼낸 refresh 토큰을 받아서 → 검사하고 → 새 access 토큰을 돌려주기
async def refresh_access_token(db: AsyncSession, refresh_token: str | None) -> str:
    # 1. 토큰을 풀어서 user_id 꺼내기 (쿠키가 없으면 refresh_token이 None)
    user_id = decode_token(refresh_token or "", REFRESH_TOKEN_TYPE)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="다시 로그인해주세요.")        # 401 : 토큰 문제, 회원 없음

    # 2. 회원 찾기 (탈퇴한 회원은 못 찾음)
    user = await user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="다시 로그인해주세요.")        # 401 : 토큰 문제, 회원 없음

    # 3. 비활성 회원 막기
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 사용자입니다.")      # 403 : 비활성

    # 4. 새 access 토큰 만들어서 돌려주기
    return create_access_token(user.id)

# ===== [박유정] 내 정보 조회 / 수정 / 탈퇴 =====


# ===== [이명석] 비밀번호 변경 / 회원 목록 / 권한 변경 =====
