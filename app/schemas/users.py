import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.enums import Department, Gender, UserRole

# ===== 공통 검증 =====

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_PATTERN = re.compile(r"^01[0-9]{8,9}$")


def validate_email(value: str) -> str:
    if not EMAIL_PATTERN.match(value):
        raise ValueError("올바른 이메일 형식이 아닙니다.")
    return value


def validate_password(value: str) -> str:
    if not 8 <= len(value) <= 20:
        raise ValueError("비밀번호는 8자 이상 20자 이하여야 합니다.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("비밀번호에 대문자가 1개 이상 포함되어야 합니다.")
    if not re.search(r"[^a-zA-Z0-9]", value):
        raise ValueError("비밀번호에 특수문자가 1개 이상 포함되어야 합니다.")
    return value


def validate_phone(value: str) -> str:
    # 프론트에서 숫자만 보내므로 하이픈 없이 01로 시작하는 10-11자리만 허용
    if not PHONE_PATTERN.match(value):
        raise ValueError("휴대폰 번호는 하이픈 없이 01로 시작하는 10-11자리 숫자여야 합니다.")
    return value


EmailType = Annotated[str, Field(max_length=255), AfterValidator(validate_email)]
PasswordType = Annotated[str, AfterValidator(validate_password)]
NameType = Annotated[str, Field(min_length=2, max_length=20)]
PhoneType = Annotated[str, AfterValidator(validate_phone)]


# ===== 공통 응답 =====

class UserResponse(BaseModel):
    # 비밀번호(hashed_password)는 응답에 포함하지 않음
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: UserRole
    is_active: bool


class TokenResponse(BaseModel):
    # 로그인(김도엽)과 토큰 재발급(김지연)이 함께 사용
    access_token: str
    token_type: str = "bearer"
    # Access Token 만료까지 남은 시간(초). 설정값에서 계산하므로 직접 넣지 않아도 됨
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


class MessageResponse(BaseModel):
    # 로그아웃, 비밀번호 변경처럼 안내 문구만 돌려줄 때 사용
    message: str


# ===== [김지연] 회원가입 =====

class SignupRequest(BaseModel):
    email: EmailType
    password: PasswordType
    name: NameType
    department: Department
    gender: Gender
    phone_number: PhoneType


# ===== [김도엽] 로그인 / 로그아웃 =====


# ===== [김지연] 토큰 재발급 =====


# ===== [박유정] 내 정보 조회 / 수정 / 탈퇴 =====


# ===== [이명석] 비밀번호 변경 / 회원 목록 / 권한 변경 =====
