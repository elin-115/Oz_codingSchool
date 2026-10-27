from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import MedicalRecord

# ===== 공통 응답 =====

class MedicalRecordListResponse(BaseModel):
    # 환자별 진료기록 목록의 한 줄 (API 7)
    model_config = ConfigDict(from_attributes=True)

    id: int
    chart_number: str
    symptoms: str  # 100자 초과 시 앞 100자 + "…" (아래 [이명석] 섹션에서 처리)
    created_at: datetime


class MedicalRecordResponse(BaseModel):
    # 진료기록 등록(API 6)·상세 조회(API 8) 응답
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_image_url: str | None
    created_at: datetime

    @classmethod
    def from_record(cls, record: MedicalRecord) -> "MedicalRecordResponse":
        # X-Ray 이미지는 별도 테이블이라 직접 꺼내서 넣음. record.xray_images를 미리 불러와야 함(selectinload)
        image = record.xray_images[0] if record.xray_images else None
        return cls(
            id=record.id,
            patient_id=record.patient_id,
            chart_number=record.chart_number,
            symptoms=record.symptoms,
            xray_image_url=image.image_url if image else None,
            created_at=record.created_at,
        )


# ===== [김지연] 진료기록 등록 =====
# 요청은 FormData(patient_id, chart_number, symptoms, xray_image)라 apis에서 Form(), UploadFile로 받음


# ===== [이명석] 환자별 진료기록 목록 / 진료기록 상세 =====
# 목록: MedicalRecordListResponse의 symptoms가 100자를 넘으면 잘라서 응답 (field_validator 등)
# 상세: 공통 MedicalRecordResponse.from_record 사용
