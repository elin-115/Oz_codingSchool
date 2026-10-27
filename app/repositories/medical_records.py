from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MedicalRecord

# 진료기록과 X-Ray 이미지의 DB 조회·저장만 담당한다.


# ===== [김지연] 진료기록 등록 =====


# ===== [박유정] 환자별 진료기록 목록 / 진료기록 상세 =====
# 상세는 X-Ray 이미지를 함께 불러온다: .options(selectinload(MedicalRecord.xray_images))
