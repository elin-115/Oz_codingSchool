"""make heatmap_url nullable

Revision ID: a1c3e5f7b9d2
Revises: 78d9440bd099
Create Date: 2026-10-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c3e5f7b9d2'
down_revision: Union[str, Sequence[str], None] = '78d9440bd099'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 히트맵은 선택사항이라 NULL 허용 (Day06 설계 3장)
    op.alter_column('ai_analysis_results', 'heatmap_url', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # 되돌리기 전에 NULL로 저장된 행은 빈 문자열로 채워야 NOT NULL로 바꿀 수 있음
    op.execute("UPDATE ai_analysis_results SET heatmap_url = '' WHERE heatmap_url IS NULL")
    op.alter_column('ai_analysis_results', 'heatmap_url', existing_type=sa.String(length=255), nullable=False)
