from fastapi import APIRouter, status

from app.core.dependencies import DBSession, MedicalUser, StaffUser
from app.schemas.medical_records import MedicalRecordListResponse, shorten_symptoms
from app.schemas.patients import PatientResponse
from app.schemas.users import MessageResponse
from app.services import medical_records as medical_record_service
from app.services import patients as patient_service

patient_router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])

# 권한: 등록은 MedicalUser(의료진), 나머지는 StaffUser(승인된 회원). 타입 자리에 바로 사용 (Depends로 감싸지 않음)

# ===== [김도엽] 환자 등록 POST "" · 환자 목록 조회 GET "" =====

from typing import Annotated
from fastapi import Query
from app.schemas.patients import PatientCreate, PatientListQuery

@patient_router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    data: PatientCreate,
    db: DBSession,
    user: MedicalUser,
):
    return await patient_service.create_patient(db, data)


@patient_router.get("", response_model=list[PatientResponse])
async def get_patient_list(
    db: DBSession,
    user: StaffUser,
    params: Annotated[PatientListQuery, Query()],
):
    return await patient_service.get_patient_list(db, params)


# ===== [이명석] 환자 상세 조회 GET /{patient_id} · 환자 정보 수정 PATCH /{patient_id} =====
from fastapi import status
from app.schemas.patients import PatientUpdateRequest

@patient_router.get("/{patient_id}", status_code=status.HTTP_200_OK)
async def get_patient(
    patient_id: int,
    db: DBSession,
    staff: StaffUser,
) -> PatientResponse:
    # 승인된 회원만 환자 상세 정보를 조회할 수 있다.
    patient = await patient_service.get_patient(db, patient_id)
    return PatientResponse.model_validate(patient)


@patient_router.patch("/{patient_id}", status_code=status.HTTP_200_OK)
async def update_patient(
    patient_id: int,
    data: PatientUpdateRequest,
    db: DBSession,
    staff: StaffUser,
) -> PatientResponse:
    # 요청에 포함된 이름·전화번호만 수정하고 갱신된 환자 정보를 반환한다.
    patient = await patient_service.update_patient(db, patient_id, data)
    return PatientResponse.model_validate(patient)

# ===== [김지연] 환자 정보 삭제 DELETE /{patient_id} =====
@patient_router.delete("/{patient_id}", status_code=status.HTTP_200_OK)
async def delete_patient(patient_id: int, db: DBSession, user: StaffUser) -> MessageResponse:
    await patient_service.delete_patient(db, patient_id)
    return MessageResponse(message="환자 정보와 관련 데이터가 모두 삭제되었습니다.")


# ===== [박유정] 환자별 진료기록 목록 GET /{patient_id}/medical-records =====
# 주소가 /patients 아래라 이 파일에 작성 (로직은 services/medical_records.py)

@patient_router.get("/{patient_id}/medical-records")
async def get_patient_medical_records(
    patient_id: int, user: StaffUser, db: DBSession
) -> list[MedicalRecordListResponse]:
    records = await medical_record_service.get_patient_records(db, patient_id)
    responses = []
    for record in records:
        item = MedicalRecordListResponse.model_validate(record)
        item.symptoms = shorten_symptoms(item.symptoms)
        responses.append(item)
    return responses