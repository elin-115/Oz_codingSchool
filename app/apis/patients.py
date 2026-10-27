from fastapi import APIRouter

from app.core.dependencies import DBSession, MedicalUser, StaffUser
from app.schemas.patients import PatientResponse
from app.services import patients as patient_service

patient_router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])

# 권한: 등록은 MedicalUser(의료진), 나머지는 StaffUser(승인된 회원). 타입 자리에 바로 사용 (Depends로 감싸지 않음)


# ===== [김도엽] 환자 등록 POST "" · 환자 목록 조회 GET "" =====


# ===== [박유정] 환자 상세 조회 GET /{patient_id} · 환자 정보 수정 PATCH /{patient_id} =====


# ===== [김지연] 환자 정보 삭제 DELETE /{patient_id} =====


# ===== [이명석] 환자별 진료기록 목록 GET /{patient_id}/medical-records =====
# 주소가 /patients 아래라 이 파일에 작성 (로직은 services/medical_records.py)
