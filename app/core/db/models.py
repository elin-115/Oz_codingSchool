import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7


class UUIDMixin:
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        CHAR(36), primary_key=True, default=uuid7
    )


class TimestampMixin:
    # datetime.now(UTC)를 바로 넣으면 서버 시작 시각 하나로 고정되므로, 저장할 때마다 호출되도록 lambda로 전달
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=text("current_timestamp(0)")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(UTC), server_default=text("current_timestamp(0)")
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 기존 행이 있는 테이블에 컬럼을 추가할 때도 False로 채워지도록 server_default 지정
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
