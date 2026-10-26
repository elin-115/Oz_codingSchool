from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

# DB 조회·저장만 담당. 탈퇴(삭제 표시)한 회원은 조회 대상에서 제외한다.


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.is_deleted.is_(False)))
    return result.scalar_one_or_none()


async def exists_email(db: AsyncSession, email: str) -> bool:
    # unique 제약은 탈퇴 회원에게도 걸리므로 삭제 여부와 관계없이 확인
    result = await db.execute(select(User.id).where(User.email == email))
    return result.first() is not None


async def exists_phone_number(db: AsyncSession, phone_number: str) -> bool:
    result = await db.execute(select(User.id).where(User.phone_number == phone_number))
    return result.first() is not None


async def create_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ===== [김도엽] 로그인 / 로그아웃 =====


# ===== [박유정] 내 정보 조회 / 수정 / 탈퇴 =====


# ===== [이명석] 비밀번호 변경 / 회원 목록 / 권한 변경 =====
