from fastapi import APIRouter

from app.core.dependencies import DBSession, MedicalUser, StaffUser
from app.schemas.medical_records import MedicalRecordResponse
from app.services import medical_records as medical_record_service

medical_record_router = APIRouter(prefix="/api/v1/medical-records", tags=["Medical Records"])

# 권한: 등록은 MedicalUser(의료진), 상세 조회는 StaffUser(승인된 회원)


# ===== [김지연] 진료기록 등록 POST "" =====


# ===== [이명석] 진료기록 상세 조회 GET /{record_id} =====
