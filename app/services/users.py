from datetime import UTC, datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.users import ChangePasswordRequest, ChangeUserRoleRequest

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
from app.schemas.users import SignupRequest, UserUpdateRequest

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
async def update_me(db: AsyncSession, user: User, data: UserUpdateRequest) -> User:
    # 보낸 항목 꺼내기
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 항목을 하나 이상 입력해 주세요."
        )
    # 휴대폰 번호 변경 시 중복 확인(변경 없을 때는 통과)
    new_phone = update_data.get("phone_number")
    if new_phone and new_phone != user.phone_number:
        if await user_repository.exists_phone_number(db, new_phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 휴대폰 번호입니다."
            )
    for field, value in update_data.items():
        setattr(user, field, value)
    return await user_repository.save_user(db, user)

async def withdraw(db: AsyncSession, user: User) -> None:
    # 즉시 삭제 대신 삭제 표시 + 개인 정보 삭제
    user.is_deleted = True
    user.deleted_at = datetime.now(UTC)
    user.is_active = False

    # 이메일・휴대폰 번호 고유 정보 처리(동일 정보로 재가입 가능)
    user.email = f"deleted_{user.id}@deleted.local"
    user.phone_number = f"deleted_{user.id}"
    user.name = "탈퇴회원"
    user.hashed_password = ""
    await user_repository.save_user(db, user)
    
# ===== [이명석] 비밀번호 변경 / 회원 목록 / 권한 변경 =====
async def change_password(db: AsyncSession, user: User, data: ChangePasswordRequest) -> None:
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="기존 비밀번호가 일치하지 않습니다.")
    if data.old_password == data.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="새 비밀번호가 기존 비밀번호와 같습니다.")
    await user_repository.update_user_password(db, user, hash_password(data.new_password))


# 회원 목록 조회
async def get_user_list(db: AsyncSession) -> list[User]:
    return await user_repository.get_user_list(db)


# 권한 변경
async def change_user_role(db: AsyncSession, admin: User, data: ChangeUserRoleRequest) -> User:
    if data.user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="본인의 권한은 변경할 수 없습니다.")
    user = await user_repository.get_user_by_id(db, data.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 회원을 찾을 수 없습니다.")
    return await user_repository.update_user_role(db, user, data.new_role)
