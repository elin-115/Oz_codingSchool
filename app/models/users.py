from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.core.enums import Department, Gender, UserRole

if TYPE_CHECKING:
    from app.models.xray_images import XrayImage


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # ERD는 integer지만, xray_images.uploader_id(bigint)가 참조하므로 타입을 맞춰 BigInteger 사용
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(20))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    department: Mapped[Department] = mapped_column(Enum(Department))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.PENDING)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 이 사용자가 업로드한 X-ray 이미지 목록
    uploaded_xray_images: Mapped[list["XrayImage"]] = relationship(back_populates="uploader")
