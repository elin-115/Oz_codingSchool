from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.ai_analysis_results import AIAnalysisResult
    from app.models.patients import Patient
    from app.models.xray_images import XrayImage


class MedicalRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 진료 기록이 남아 있는 환자는 실제로 삭제되지 않도록 RESTRICT
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="RESTRICT"), index=True
    )
    chart_number: Mapped[str] = mapped_column(String(50), unique=True)
    symptoms: Mapped[str] = mapped_column(Text)

    # 진료 기록의 환자
    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    # 진료 기록에 연결된 X-ray 이미지, AI 분석 결과
    xray_images: Mapped[list["XrayImage"]] = relationship(back_populates="medical_record")
    ai_analysis_results: Mapped[list["AIAnalysisResult"]] = relationship(back_populates="medical_record")
