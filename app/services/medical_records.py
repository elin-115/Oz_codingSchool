from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MedicalRecord
from app.repositories import medical_records as medical_record_repository
from app.services import patients as patient_service

# 진료기록의 비즈니스 규칙을 담당한다. 환자가 있는지는 patient_service.get_patient_or_404로 확인한다.


# ===== [김지연] 진료기록 등록 =====


# ===== [박유정] 환자별 진료기록 목록 / 진료기록 상세 =====
# 없는 진료기록이면 404 "진료 기록을 찾을 수 없습니다."

async def get_patient_records(db: AsyncSession, patient_id: int) -> list[MedicalRecord]:
    # 환자 없음(삭제된 환자 포함) 404 "환자를 찾을 수 없습니다." 출력
    await patient_service.get_patient_or_404(db, patient_id)
    # 환자 있음(진료기록만 없음) 빈목록[] 그대로 출력
    return await medical_record_repository.get_records_by_patient_id(db, patient_id)


async def get_record_or_404(db: AsyncSession, record_id: int) -> MedicalRecord:
    record = await medical_record_repository.get_record_by_id(db, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="진료 기록을 찾을 수 없습니다.")
    return record