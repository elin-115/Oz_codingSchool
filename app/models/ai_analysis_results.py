from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.medical_records import MedicalRecord


class AIAnalysisResult(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 분석 결과가 남아 있는 진료 기록은 실제로 삭제되지 않도록 RESTRICT
    record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("medical_records.id", ondelete="RESTRICT"), index=True
    )
    is_pneumonia: Mapped[bool] = mapped_column(Boolean)
    # 신뢰도(%)는 0~100 사이만 저장되도록 DB에서 검증
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), CheckConstraint("confidence >= 0 AND confidence <= 100")
    )
    # 히트맵은 요구사항상 선택사항이라 비워둘 수 있게 함 (Day06 설계 3장)
    heatmap_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_model: Mapped[str] = mapped_column(String(50))

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="ai_analysis_results")
