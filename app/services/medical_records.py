from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import medical_records as medical_record_repository
from app.services import patients as patient_service

# 진료기록의 비즈니스 규칙을 담당한다. 환자가 있는지는 patient_service.get_patient_or_404로 확인한다.


# ===== [김지연] 진료기록 등록 =====


# ===== [이명석] 환자별 진료기록 목록 / 진료기록 상세 =====
# 없는 진료기록이면 404 "진료 기록을 찾을 수 없습니다."
