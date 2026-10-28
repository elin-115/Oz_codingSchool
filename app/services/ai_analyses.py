from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.files import media_url_to_path
from app.models import AIAnalysisResult
from app.repositories import ai_analyses as ai_analysis_repository
from app.services import medical_records as medical_record_service
from worker import model as ai_model

# AI 예측의 비즈니스 규칙을 담당한다. 진료기록이 있는지는 medical_record_service.get_record_or_404로 확인한다.
# 모델 코드는 worker/model.py: ai_model.MODEL_NAME, ai_model.predict(image_path) -> PredictionResult


# ===== [김도엽] AI 폐렴 예측 =====
# 1) get_record_or_404로 진료기록 + X-Ray 이미지 조회
# 2) 같은 진료기록 + 같은 모델(ai_model.MODEL_NAME) 결과가 있으면 추론 없이 그 결과를 돌려줌 (API에서 200)
# 3) 이미지 기록이 없거나 파일이 없으면 404 "X-Ray 이미지 파일을 찾을 수 없습니다."
#    경로: media_url_to_path(record.xray_images[0].image_url)
# 4) predict는 CPU를 쓰는 일반 함수라 await run_in_threadpool(ai_model.predict, path)로 호출
#    모델이 안 올라왔으면 predict가 ModelNotLoadedError를 냄 → 503 "AI 모델이 준비되지 않았습니다."
# 5) AIAnalysisResult(record_id, is_pneumonia, confidence, heatmap_url=None, ai_model=ai_model.MODEL_NAME) 저장 (API에서 201)
# 새로 예측했는지도 API가 알아야 상태 코드를 고를 수 있음 (예: (결과, 새로 만들었는지) 튜플로 반환)


# ===== [박유정] AI 예측 결과 목록 조회 =====
# 진료기록이 없으면 404 (get_record_or_404), 결과가 없으면 빈 목록 []
async def get_record_analyses(db: AsyncSession, record_id: int) -> list[AIAnalysisResult]:
    # 진료기록 없음 404 "진료 기록을 찾을 수 없습니다." 출력
    await medical_record_service.get_record_or_404(db, record_id)
    # 진료기록 있음(예측 결과 없음) 빈목록[] 그대로 출력
    return await ai_analysis_repository.get_analyses_by_record_id(db, record_id)
