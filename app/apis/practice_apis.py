# app/apis/practice_apis.py
import re
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel, Field

user_list = [
    {
        "id": 1,
        "name": "홍길동",
        "age": 24,
        "email": "gildong24@example.com",
        "password": "Password1234!!",
    },
    {
        "id": 2,
        "name": "장문복",
        "age": 21,
        "email": "moonluck12@example.com",
        "password": "Check1321!",
    },
    {
        "id": 3,
        "name": "임우진",
        "age": 31,
        "email": "limousine33@example.com",
        "password": "lwsPAssword12@",
    },
]

practice_router = APIRouter(prefix="/practice_api/users", tags=["Practice"])


# ===== 공통 검증 함수 =====

# 이메일 형식: 아이디@도메인.최상위도메인
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_password(value: str) -> str:
    # 8자 이상 20자 이하인지 검증
    if not 8 <= len(value) <= 20:
        raise ValueError("비밀번호는 8자 이상 20자 이하여야 합니다.")

    # 대문자가 포함되어 있는지 검증
    if not re.search(r"[A-Z]", value):
        raise ValueError("비밀번호에 대문자가 1개 이상 포함되어야 합니다.")

    # 특수문자가 포함되어 있는지 검증
    if not re.search(r"[^a-zA-Z0-9]", value):
        raise ValueError("비밀번호에 특수문자가 1개 이상 포함되어야 합니다.")

    return value


def validate_email(value: str) -> str:
    # 정규표현식으로 이메일 형식 검증
    if not EMAIL_PATTERN.match(value):
        raise ValueError("올바른 이메일 형식이 아닙니다.")

    return value


# 생성·수정 요청 스키마에서 같이 쓰는 타입
NameType = Annotated[str, Field(min_length=2, max_length=10)]
AgeType = Annotated[int, Field(ge=14)]
EmailType = Annotated[str, Field(max_length=30), AfterValidator(validate_email)]
PasswordType = Annotated[str, AfterValidator(validate_password)]


def find_user(user_id: int) -> dict:
    # user_list에서 id가 일치하는 회원 찾기
    user = next((user for user in user_list if user["id"] == user_id), None)

    # 회원이 없으면 404 Not Found 응답으로 반환
    if user is None:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")

    return user


# ===== 응답 스키마 =====

class UserResponse(BaseModel):
    # 응답에는 password를 포함하지 않음
    id: int
    name: str
    age: int
    email: str


# ===== API =====

# [김지연] 모든 회원 목록 조회
@practice_router.get("", status_code=200)
async def get_user_list() -> list[UserResponse]:
    return [UserResponse.model_validate(user) for user in user_list]


# [A] 회원 상세 조회 - GET /{user_id}


# [B] 회원 생성 - POST ""


# [C] 회원 정보 수정 - PATCH /{user_id}


# [A] 회원 삭제 - DELETE /{user_id}
