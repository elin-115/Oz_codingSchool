from fastapi import APIRouter, Response, status

from app.core.dependencies import DBSession, StaffUser
from app.schemas.ai_analyses import AIAnalysisResponse
from app.services import ai_analyses as ai_analysis_service

# 주소는 진료기록 아래(/medical-records/{record_id}/...)지만 담당이 달라 파일을 나눔
ai_analysis_router = APIRouter(prefix="/api/v1/medical-records", tags=["AI Analyses"])

# 권한: 예측·목록 모두 StaffUser(승인된 회원). 의료인·개발팀·연구자 = 전 부서


# ===== [김도엽] AI 폐렴 예측 POST /{record_id}/predict =====
# 새로 예측하면 201, 같은 모델로 저장된 결과를 돌려주면 200 (response.status_code로 바꿈)
@ai_analysis_router.post("/{record_id}/predict", status_code=status.HTTP_201_CREATED)
async def predict_medical_record(
    record_id: int,
    response: Response,
    db: DBSession,
    user: StaffUser,
) -> AIAnalysisResponse:
    result, created = await ai_analysis_service.predict_record(db, record_id)

    if not created:
        response.status_code = status.HTTP_200_OK

    return AIAnalysisResponse.model_validate(result)


# ===== [박유정] AI 예측 결과 목록 조회 GET /{record_id}/analyses =====
# 응답: list[AIAnalysisResponse] (최신순)
@ai_analysis_router.get("/{record_id}/analyses")
async def get_record_analyses(record_id: int, user: StaffUser, db: DBSession) -> list[AIAnalysisResponse]:
    # user: StaffUser (승인된 user만 열람 가능, 대기자는 403)
    analyses = await ai_analysis_service.get_record_analyses(db, record_id)
    return [AIAnalysisResponse.model_validate(analysis) for analysis in analyses]
