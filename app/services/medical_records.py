from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.files import delete_media_file, save_xray_image
from app.models import MedicalRecord, User, XrayImage
from app.repositories import medical_records as medical_record_repository
from app.services import patients as patient_service

# 진료기록의 비즈니스 규칙을 담당한다. 환자가 있는지는 patient_service.get_patient_or_404로 확인한다.


# ===== [김지연] 진료기록 등록 =====
# 업로드할 수 있는 이미지 종류(Content-Type)와 저장할 확장자
XRAY_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg"}
MAX_XRAY_SIZE = 10 * 1024 * 1024  # 10MB


async def create_medical_record(
    db: AsyncSession,
    user: User,
    patient_id: int,
    chart_number: str,
    symptoms: str,
    xray_image: UploadFile,
) -> MedicalRecord:
    await patient_service.get_patient_or_404(db, patient_id)
    if await medical_record_repository.exists_chart_number(db, chart_number):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 진료 차트 넘버입니다.")

    # 파일 확장자 이름은 바꿀 수 있으므로, 브라우저가 알려준 파일 종류(Content-Type)로 확인
    extension = XRAY_EXTENSIONS.get(xray_image.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="png 또는 jpeg 이미지만 업로드할 수 있습니다.")
    content = await xray_image.read()
    if len(content) > MAX_XRAY_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미지는 10MB 이하만 업로드할 수 있습니다.")

    image_url = save_xray_image(content, extension)
    record = MedicalRecord(
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        # 촬영일시는 프론트에 입력 칸이 없어 업로드한 시각으로 저장 (설계 문서 3장)
        xray_images=[
            XrayImage(uploader_id=user.id, image_url=image_url, shooting_datetime=datetime.now(UTC))
        ],
    )
    try:
        return await medical_record_repository.create_medical_record(db, record)
    except Exception:
        # DB 저장이 실패하면 사진 파일만 남지 않도록 지운다
        delete_media_file(image_url)
        raise


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