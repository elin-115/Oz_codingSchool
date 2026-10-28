
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.files import (
    delete_media_file,
    media_url_to_path,
    save_heatmap_image,
)
from app.models import AIAnalysisResult
from app.repositories import ai_analyses as ai_analysis_repository
from app.services import medical_records as medical_record_service
from worker import model as ai_model

# AI 예측의 비즈니스 규칙을 담당한다.
# 진료기록 존재 여부는 medical_record_service.get_record_or_404로 확인한다.
# 모델 코드는 worker/model.py의 ai_model.MODEL_NAME, ai_model.predict(), ai_model.make_heatmap()을 사용한다.


# ===== [김도엽] AI 폐렴 예측 =====

async def predict_record(
    db: AsyncSession,
    record_id: int,
) -> tuple[AIAnalysisResult, bool]:
    # 1. 진료기록 조회. 없으면 기존 서비스가 404 처리
    record = await medical_record_service.get_record_or_404(db, record_id)

    # 2. 동일 진료기록·모델의 기존 결과 확인
    existing = await ai_analysis_repository.get_existing_result(
        db,
        record_id,
        ai_model.MODEL_NAME,
    )
    if existing is not None:
        return existing, False

    # 3. X-Ray 이미지 기록 확인
    if not record.xray_images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-Ray 이미지 파일을 찾을 수 없습니다.",
        )

    # 4. 이미지 경로 및 실제 파일 확인
    image_path = media_url_to_path(record.xray_images[0].image_url)
    if image_path is None or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-Ray 이미지 파일을 찾을 수 없습니다.",
        )


    # 5. AI 예측 및 히트맵 생성
    try:
        prediction = await run_in_threadpool(ai_model.predict, image_path)
        heatmap = await run_in_threadpool(ai_model.make_heatmap, image_path)
    except ai_model.ModelNotLoadedError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 모델이 준비되지 않았습니다.",
        ) from None

    # 6. 히트맵 이미지 파일 저장
    heatmap_url = await run_in_threadpool(save_heatmap_image, heatmap)

    # 7. 예측 결과 저장
    analysis = AIAnalysisResult(
        record_id=record_id,
        is_pneumonia=prediction.is_pneumonia,
        confidence=prediction.confidence,
        heatmap_url=heatmap_url,
        ai_model=ai_model.MODEL_NAME,
    )

    try:
        saved = await ai_analysis_repository.create_analysis(db, analysis)
    except Exception:
        try:
            await db.rollback()
        finally:
            await run_in_threadpool(delete_media_file, heatmap_url)
        raise

    return saved, True


# ===== [박유정] AI 예측 결과 목록 조회 =====
# 진료기록이 없으면 404 (get_record_or_404), 결과가 없으면 빈 목록 []
async def get_record_analyses(db: AsyncSession, record_id: int) -> list[AIAnalysisResult]:
    # 진료기록 없음 404 "진료 기록을 찾을 수 없습니다." 출력
    await medical_record_service.get_record_or_404(db, record_id)
    # 진료기록 있음(예측 결과 없음) 빈목록[] 그대로 출력
    return await ai_analysis_repository.get_analyses_by_record_id(db, record_id)
