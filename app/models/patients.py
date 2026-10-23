from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.core.enums import Gender

if TYPE_CHECKING:
    from app.models.medical_records import MedicalRecord


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    age: Mapped[int] = mapped_column(SmallInteger)
    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    phone: Mapped[str] = mapped_column(String(11))

    # 환자의 진료 기록 목록 (환자 삭제 시 진료 기록도 함께 삭제)
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
