from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ===== 공통 응답 =====


class AIAnalysisResponse(BaseModel):
    # AI 예측(API 9) 응답, 예측 결과 목록(API 10)의 한 줄
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float  # DB는 Decimal이라 그대로 두면 JSON에 문자열로 나가므로 float로 받음
    heatmap_url: str | None
    ai_model: str
    created_at: datetime
