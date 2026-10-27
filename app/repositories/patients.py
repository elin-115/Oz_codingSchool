from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Patient

# DB 조회·저장만 담당. 삭제 표시된 환자는 조회 대상에서 제외한다.


async def get_patient_by_id(db: AsyncSession, patient_id: int) -> Patient | None:
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_deleted.is_(False)))
    return result.scalar_one_or_none()


# ===== [김도엽] 환자 등록 / 환자 목록 조회 =====


# ===== [박유정] 환자 상세 조회 / 환자 정보 수정 =====


# ===== [김지연] 환자 정보 삭제 =====
