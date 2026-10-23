from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.medical_records import MedicalRecord
    from app.models.users import User


class XrayImage(Base, SoftDeleteMixin):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 이미지가 남아 있는 진료 기록은 실제로 삭제되지 않도록 RESTRICT
    record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("medical_records.id", ondelete="RESTRICT"), index=True
    )
    # ERD상 NOT NULL이므로 업로더가 있는 사용자는 삭제되지 않도록 RESTRICT
    uploader_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    image_url: Mapped[str] = mapped_column(String(2048))
    shooting_datetime: Mapped[datetime] = mapped_column(DateTime)
    # ERD에 updated_at이 없어서 TimestampMixin 대신 created_at만 작성
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=text("current_timestamp(0)")
    )

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="xray_images")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_xray_images")
