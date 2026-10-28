from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysisResult

# AI 예측 결과의 DB 조회·저장만 담당한다.


# ===== [김도엽] AI 폐렴 예측 =====
async def get_existing_result(
    db: AsyncSession,
    record_id: int,
    ai_model: str,
) -> AIAnalysisResult | None:
    query = (
        select(AIAnalysisResult)
        .where(
            AIAnalysisResult.record_id == record_id,
            AIAnalysisResult.ai_model == ai_model,
            AIAnalysisResult.is_deleted.is_(False),
        )
        .order_by(AIAnalysisResult.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_analysis(
    db: AsyncSession,
    analysis: AIAnalysisResult,
) -> AIAnalysisResult:
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis

# ===== [박유정] AI 예측 결과 목록 조회 =====
# 진료기록 하나의 예측 결과 전체 (삭제 표시 제외, 최신순)
async def get_analyses_by_record_id(db: AsyncSession, record_id: int) -> list[AIAnalysisResult]:
    result = await db.execute(
        select(AIAnalysisResult)
        .where(AIAnalysisResult.record_id == record_id, AIAnalysisResult.is_deleted.is_(False))
        .order_by(AIAnalysisResult.created_at.desc(), AIAnalysisResult.id.desc())
    )
    return list(result.scalars().all())
