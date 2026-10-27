from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.enums import Gender
from app.schemas.users import PhoneType

# ===== 공통 검증 =====

# Field(min_length=..)의 기본 오류는 영어라, 프론트 알림에 한글이 보이도록 직접 검사 (users의 validate_phone과 같은 방식)
def validate_patient_name(value: str) -> str:
    if not 2 <= len(value) <= 30:  # DB String(30)
        raise ValueError("이름은 2자 이상 30자 이하여야 합니다.")
    return value


def validate_age(value: int) -> int:
    if not 0 <= value <= 150:
        raise ValueError("나이는 0세 이상 150세 이하여야 합니다.")
    return value


PatientNameType = Annotated[str, AfterValidator(validate_patient_name)]
AgeType = Annotated[int, AfterValidator(validate_age)]


# ===== 공통 응답 =====


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    gender: Gender
    # DB 컬럼은 ERD대로 phone, 프론트(static/pages.js)는 phone_number로 읽으므로 이름만 바꿔서 응답
    phone_number: str = Field(validation_alias="phone")
    created_at: datetime
    updated_at: datetime | None


# ===== [김도엽] 환자 등록 / 환자 목록 조회 =====
class PatientCreate(BaseModel):
    name: PatientNameType
    age: AgeType
    gender: Gender
    phone_number: PhoneType


class PatientListQuery(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    gender: Gender | None = None
    min_age: AgeType | None = None
    max_age: AgeType | None = None


# ===== [이명석] 환자 상세 조회 / 환자 정보 수정 =====
# 상세 조회는 공통 PatientResponse 사용
# 수정 요청: name, phone_number 둘 다 선택 (나이·성별은 수정 불가)
class PatientUpdateRequest(BaseModel):
    name: PatientNameType | None = None
    phone_number: PhoneType | None = None


# ===== [김지연] 환자 정보 삭제 =====
# 응답은 app.schemas.users의 MessageResponse 사용
