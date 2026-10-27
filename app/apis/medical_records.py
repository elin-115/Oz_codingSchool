from typing import Annotated

from fastapi import APIRouter, Form, UploadFile, status

from app.core.dependencies import DBSession, MedicalUser, StaffUser
from app.schemas.medical_records import MedicalRecordResponse
from app.services import medical_records as medical_record_service

medical_record_router = APIRouter(prefix="/api/v1/medical-records", tags=["Medical Records"])

# 권한: 등록은 MedicalUser(의료진), 상세 조회는 StaffUser(승인된 회원)


# ===== [김지연] 진료기록 등록 POST "" =====
# 프론트가 파일과 함께 FormData로 보내므로 JSON 본문 대신 Form(), UploadFile로 받음
@medical_record_router.post("", status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    db: DBSession,
    user: MedicalUser,          # 등록은 의료진만
    patient_id: Annotated[int, Form()],
    chart_number: Annotated[str, Form(min_length=1, max_length=50)],
    symptoms: Annotated[str, Form(min_length=1)],
    xray_image: UploadFile,     # Swagger에서 "파일 선택" 버튼
) -> MedicalRecordResponse:
    record = await medical_record_service.create_medical_record(
        db, user, patient_id, chart_number, symptoms, xray_image
    )
    return MedicalRecordResponse.from_record(record)    # from_record: X-Ray 주소까지 꺼내서 응답을 만들어 줌


# ===== [박유정] 진료기록 상세 조회 GET /{record_id} =====
