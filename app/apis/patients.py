from fastapi import APIRouter

from app.core.dependencies import DBSession, MedicalUser, StaffUser
from app.schemas.medical_records import MedicalRecordListResponse, shorten_symptoms
from app.schemas.patients import PatientResponse
from app.services import medical_records as medical_record_service
from app.services import patients as patient_service

patient_router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])

# 권한: 등록은 MedicalUser(의료진), 나머지는 StaffUser(승인된 회원). 타입 자리에 바로 사용 (Depends로 감싸지 않음)


# ===== [김도엽] 환자 등록 POST "" · 환자 목록 조회 GET "" =====


# ===== [이명석] 환자 상세 조회 GET /{patient_id} · 환자 정보 수정 PATCH /{patient_id} =====


# ===== [김지연] 환자 정보 삭제 DELETE /{patient_id} =====


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