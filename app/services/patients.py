from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.files import delete_media_file
from app.models import Patient
from app.repositories import patients as patient_repository

# 비즈니스 규칙(존재 확인, 검색 조건 검사 등)을 담당하고 DB 작업은 repository에 맡긴다.


async def get_patient_or_404(db: AsyncSession, patient_id: int) -> Patient:
    # 환자 상세·수정·삭제, 진료기록 등록·목록에서 공통으로 사용
    patient = await patient_repository.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="환자를 찾을 수 없습니다.")
    return patient


# ===== [김도엽] 환자 등록 / 환자 목록 조회 =====
# 등록: Patient(phone=data.phone_number, ...) 처럼 DB 컬럼 이름 phone에 옮겨 담기
# 목록: min_age > max_age면 400


# ===== [이명석] 환자 상세 조회 / 환자 정보 수정 =====


# ===== [김지연] 환자 정보 삭제 =====
async def delete_patient(db: AsyncSession, patient_id: int) -> None:
    await get_patient_or_404(db, patient_id)
    image_urls = await patient_repository.delete_patient(db, patient_id)
    # DB 삭제가 성공한 뒤에 이미지 파일을 지움 (DB가 실패하면 파일은 그대로 남음)
    for image_url in image_urls:
        delete_media_file(image_url)
