from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysisResult

# AI 예측 결과의 DB 조회·저장만 담당한다.


# ===== [김도엽] AI 폐렴 예측 =====
# 1) 저장된 결과 찾기: record_id와 ai_model이 같고 삭제 표시가 아닌 결과 1건 (없으면 None)
# 2) 새 결과 저장: db.add → commit → refresh(created_at을 응답에 쓰기 위해)


# ===== [박유정] AI 예측 결과 목록 조회 =====
# 진료기록 하나의 예측 결과 전체 (삭제 표시 제외, 최신순)
async def get_analyses_by_record_id(db: AsyncSession, record_id: int) -> list[AIAnalysisResult]:
    result = await db.execute(
        select(AIAnalysisResult)
        .where(AIAnalysisResult.record_id == record_id, AIAnalysisResult.is_deleted.is_(False))
        .order_by(AIAnalysisResult.created_at.desc(), AIAnalysisResult.id.desc())
    )
    return list(result.scalars().all())
