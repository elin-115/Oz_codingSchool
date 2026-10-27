from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Gender
from app.schemas.users import PhoneType

# ===== 공통 검증 =====

PatientNameType = Annotated[str, Field(min_length=2, max_length=30)]  # DB String(30)
AgeType = Annotated[int, Field(ge=0, le=150)]


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
