from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MedicalRecord

# 진료기록과 X-Ray 이미지의 DB 조회·저장만 담당한다.


# ===== [김지연] 진료기록 등록 =====


# ===== [박유정] 환자별 진료기록 목록 / 진료기록 상세 =====
# 상세는 X-Ray 이미지를 함께 불러온다: .options(selectinload(MedicalRecord.xray_images))

async def get_records_by_patient_id(db: AsyncSession, patient_id: int) -> list[MedicalRecord]:
    # 한 환자 진료기록 목록 (삭제 표시 제외, 최신순)
    result = await db.execute(
        select(MedicalRecord)
        .where(MedicalRecord.patient_id == patient_id, MedicalRecord.is_deleted.is_(False))
        .order_by(MedicalRecord.created_at.desc(), MedicalRecord.id.desc())
    )
    return list(result.scalars().all())


async def get_record_by_id(db: AsyncSession, record_id: int) -> MedicalRecord | None:
    # 진료기록 1건 + 연결된 X-ray 이미지 함께 불러오기 (삭제 표시 제외)
    result = await db.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(MedicalRecord.id == record_id, MedicalRecord.is_deleted.is_(False))
    )
    return result.scalar_one_or_none()