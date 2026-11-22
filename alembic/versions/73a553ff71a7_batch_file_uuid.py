from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '73a553ff71a7'
down_revision: Union[str, Sequence[str], None] = '623bcc5b1a7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('import_batch', sa.Column('file_uuid', sa.String(length=500), nullable=False))


def downgrade() -> None:
    op.drop_column('import_batch', 'file_uuid')
