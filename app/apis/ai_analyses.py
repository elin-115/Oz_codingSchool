from fastapi import APIRouter, Response, status

from app.core.dependencies import DBSession, StaffUser
from app.schemas.ai_analyses import AIAnalysisResponse
from app.services import ai_analyses as ai_analysis_service

# 주소는 진료기록 아래(/medical-records/{record_id}/...)지만 담당이 달라 파일을 나눔
ai_analysis_router = APIRouter(prefix="/api/v1/medical-records", tags=["AI Analyses"])

# 권한: 예측·목록 모두 StaffUser(승인된 회원). 의료인·개발팀·연구자 = 전 부서


# ===== [김도엽] AI 폐렴 예측 POST /{record_id}/predict =====
# 새로 예측하면 201, 저장된 결과를 돌려주면 200
# 상태 코드는 매개변수 response: Response를 받아 response.status_code = status.HTTP_200_OK 처럼 바꿈
# 응답: AIAnalysisResponse.model_validate(결과)


# ===== [박유정] AI 예측 결과 목록 조회 GET /{record_id}/analyses =====
# 응답: list[AIAnalysisResponse] (최신순)
