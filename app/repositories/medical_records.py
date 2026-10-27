from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MedicalRecord

# 진료기록과 X-Ray 이미지의 DB 조회·저장만 담당한다.


# ===== [김지연] 진료기록 등록 =====
async def exists_chart_number(db: AsyncSession, chart_number: str) -> bool:
    # unique 제약은 삭제 표시된 기록에도 걸리므로 삭제 여부와 관계없이 확인
    result = await db.execute(select(MedicalRecord.id).where(MedicalRecord.chart_number == chart_number))
    return result.first() is not None


async def create_medical_record(db: AsyncSession, record: MedicalRecord) -> MedicalRecord:
    # record.xray_images에 담긴 X-Ray 이미지도 함께 저장됨 (relationship)
    db.add(record)
    await db.commit()
    return record


# ===== [박유정] 환자별 진료기록 목록 / 진료기록 상세 =====
# 상세는 X-Ray 이미지를 함께 불러온다: .options(selectinload(MedicalRecord.xray_images))
