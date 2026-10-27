from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Patient

# DB 조회·저장만 담당. 삭제 표시된 환자는 조회 대상에서 제외한다.


async def get_patient_by_id(db: AsyncSession, patient_id: int) -> Patient | None:
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_deleted.is_(False)))
    return result.scalar_one_or_none()


# ===== [김도엽] 환자 등록 / 환자 목록 조회 =====


# ===== [이명석] 환자 상세 조회 / 환자 정보 수정 =====
# 환자 조회 코드는 위에 작성되어 있음
# 환자 정보 수정
async def update_patient(
    db: AsyncSession,
    patient: Patient,
    *,
    name: str | None = None,
    phone_number: str | None = None,
) -> Patient:
    # 전달된 필드만 수정하며, phone_number는 DB의 phone 컬럼에 저장한다.
    if name is not None:
        patient.name = name
    if phone_number is not None:
        patient.phone = phone_number

    await db.commit()
    await db.refresh(patient)
    return patient

# ===== [김지연] 환자 정보 삭제 =====
