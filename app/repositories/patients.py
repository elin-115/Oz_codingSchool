from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysisResult, MedicalRecord, Patient, XrayImage

# DB 조회·저장만 담당. 삭제 표시된 환자는 조회 대상에서 제외한다.


async def get_patient_by_id(db: AsyncSession, patient_id: int) -> Patient | None:
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_deleted.is_(False)))
    return result.scalar_one_or_none()


# ===== [김도엽] 환자 등록 / 환자 목록 조회 =====
async def create_patient(db: AsyncSession, patient: Patient) -> Patient:
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patient_list(db: AsyncSession, params) -> list[Patient]:
    stmt = select(Patient).where(Patient.is_deleted.is_(False))

    if params.name:
        stmt = stmt.where(Patient.name.contains(params.name))

    if params.gender:
        stmt = stmt.where(Patient.gender == params.gender)

    if params.min_age is not None:
        stmt = stmt.where(Patient.age >= params.min_age)

    if params.max_age is not None:
        stmt = stmt.where(Patient.age <= params.max_age)

    result = await db.execute(stmt.order_by(Patient.id))
    return list(result.scalars().all())


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
async def delete_patient(db: AsyncSession, patient_id: int) -> list[str]:
    # 영구 삭제(REQ-PTNT-005). FK가 RESTRICT라 자식 테이블부터 지운다
    record_ids = select(MedicalRecord.id).where(MedicalRecord.patient_id == patient_id)  # 진료기록 번호 목록

    # 행을 지우면 파일 주소를 알 수 없으므로, 지우기 전에 X-Ray 이미지 주소를 꺼내 둠
    result = await db.execute(select(XrayImage.image_url).where(XrayImage.record_id.in_(record_ids)))
    image_urls = list(result.scalars().all())

    await db.execute(delete(AIAnalysisResult).where(AIAnalysisResult.record_id.in_(record_ids)))    # AI 분석결과 삭제
    await db.execute(delete(XrayImage).where(XrayImage.record_id.in_(record_ids)))                  # X-Ray 삭제
    await db.execute(delete(MedicalRecord).where(MedicalRecord.patient_id == patient_id))           # 진료기록 삭제
    await db.execute(delete(Patient).where(Patient.id == patient_id))                               # 환자 삭제
    await db.commit()  # 한 번에 확정. 중간에 실패하면 모두 되돌려짐
    return image_urls
