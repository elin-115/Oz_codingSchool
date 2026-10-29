from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator

# ===== 공통 타입 =====


def mark_utc(value: datetime) -> datetime:
    # DB(MySQL DATETIME)는 시간대 없이 UTC 시각을 돌려주므로 "이건 UTC"라고 표시만 붙임 (값은 그대로)
    # 응답이 "...T00:14:23Z"가 되면 브라우저가 한국 시각으로 바꿔 보여줌
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


UTCDatetime = Annotated[datetime, AfterValidator(mark_utc)]
