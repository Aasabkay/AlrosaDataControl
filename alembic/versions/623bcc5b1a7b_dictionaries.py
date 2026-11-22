from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '623bcc5b1a7b'
down_revision: Union[str, Sequence[str], None] = 'b1b6bb094536'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('asset_type',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('column_alias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alias', sa.String(length=200), nullable=False),
    sa.Column('field', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alias')
    )
    op.create_index(op.f('ix_column_alias_field'), 'column_alias', ['field'], unique=False)
    op.create_table('status_synonym',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('synonym', sa.String(length=100), nullable=False),
    sa.Column('canonical', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('synonym')
    )
    op.create_index(op.f('ix_status_synonym_canonical'), 'status_synonym', ['canonical'], unique=False)
    op.create_table('asset_type_alias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alias', sa.String(length=100), nullable=False),
    sa.Column('asset_type_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['asset_type_id'], ['asset_type.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alias')
    )


def downgrade() -> None:
    op.drop_table('asset_type_alias')
    op.drop_index(op.f('ix_status_synonym_canonical'), table_name='status_synonym')
    op.drop_table('status_synonym')
    op.drop_index(op.f('ix_column_alias_field'), table_name='column_alias')
    op.drop_table('column_alias')
    op.drop_table('asset_type')
