from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2 알고리즘으로 비밀번호를 해싱 (pwdlib 권장 설정)
password_hash = PasswordHash.recommended()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    # 페이로드에는 최소 식별 정보인 user_id(sub)만 담고, 토큰 종류와 만료 시각을 함께 넣음
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": datetime.now(UTC) + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id, ACCESS_TOKEN_TYPE, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id, REFRESH_TOKEN_TYPE, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, token_type: str) -> int | None:
    # 서명이 틀리거나 만료되었거나 종류가 다르면 None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != token_type:
        return None
    return int(payload["sub"])
