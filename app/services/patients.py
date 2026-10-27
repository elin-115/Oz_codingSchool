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
from app.schemas.patients import PatientUpdateRequest

async def get_patient(db: AsyncSession, patient_id: int) -> Patient:
    # 존재하지 않거나 삭제된 환자는 공통 로직에서 404로 처리한다.
    return await get_patient_or_404(db, patient_id)


async def update_patient(
    db: AsyncSession,
    patient_id: int,
    data: PatientUpdateRequest,
) -> Patient:
    # 값이 전달된 항목만 수정 대상으로 사용한다.
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 항목을 하나 이상 입력해 주세요.",
        )

    # 수정 전에 환자의 존재 여부를 확인하고, DB 작업은 repository에 맡긴다.
    patient = await get_patient_or_404(db, patient_id)
    return await patient_repository.update_patient(db, patient, **update_data)

# ===== [김지연] 환자 정보 삭제 =====
async def delete_patient(db: AsyncSession, patient_id: int) -> None:
    await get_patient_or_404(db, patient_id)
    image_urls = await patient_repository.delete_patient(db, patient_id)
    # DB 삭제가 성공한 뒤에 이미지 파일을 지운다 (DB가 실패하면 파일은 그대로 남음)
    for image_url in image_urls:
        delete_media_file(image_url)
