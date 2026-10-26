from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
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


# ===== Refresh Token 쿠키 =====
# 로그인(심기), 토큰 재발급(읽기), 로그아웃·탈퇴(지우기)가 같은 이름과 path를 써야
# 브라우저가 쿠키를 보내고 지워주므로, 설정을 이곳 한 군데에서만 관리한다.

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/users"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,  # JavaScript에서 읽을 수 없도록
        samesite="lax",
        secure=False,  # 로컬(http) 개발용. https로 배포할 때 True로 변경
    )


def delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
