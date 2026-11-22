from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b1b6bb094536'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('reconciliation_run',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('source',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('asset',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_key', sa.String(length=100), nullable=False),
    sa.Column('match_status', sa.String(length=20), nullable=False),
    sa.Column('match_method', sa.String(length=20), nullable=True),
    sa.Column('match_score', sa.Float(), nullable=True),
    sa.Column('reconciliation_run_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['reconciliation_run_id'], ['reconciliation_run.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_asset_key'), 'asset', ['asset_key'], unique=False)
    op.create_table('import_batch',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=500), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('issue',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('field', sa.String(length=50), nullable=True),
    sa.Column('suggestion', sa.String(length=100), nullable=True),
    sa.Column('values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('batch_id', sa.Integer(), nullable=True),
    sa.Column('reconciliation_run_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ),
    sa.ForeignKeyConstraint(['reconciliation_run_id'], ['reconciliation_run.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_issue_code'), 'issue', ['code'], unique=False)
    op.create_table('raw_row',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('batch_id', sa.Integer(), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.Column('cells', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('reject_reason', sa.String(length=30), nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_raw_row_batch_row', 'raw_row', ['batch_id', 'row_number'], unique=False)
    op.create_table('source_record',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('batch_id', sa.Integer(), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.Column('inventory_number', sa.String(length=50), nullable=True),
    sa.Column('serial_number', sa.String(length=100), nullable=True),
    sa.Column('name', sa.String(length=300), nullable=True),
    sa.Column('asset_type', sa.String(length=100), nullable=True),
    sa.Column('category', sa.String(length=20), nullable=True),
    sa.Column('manufacturer', sa.String(length=200), nullable=True),
    sa.Column('model', sa.String(length=200), nullable=True),
    sa.Column('specs', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('status_raw', sa.String(length=100), nullable=True),
    sa.Column('responsible_person', sa.String(length=200), nullable=True),
    sa.Column('location', sa.String(length=500), nullable=True),
    sa.Column('commissioning_date', sa.Date(), nullable=True),
    sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['asset.id'], ),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_source_record_batch_row', 'source_record', ['batch_id', 'row_number'], unique=False)
    op.create_table('issue_ref',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('issue_id', sa.Integer(), nullable=False),
    sa.Column('batch_id', sa.Integer(), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ),
    sa.ForeignKeyConstraint(['issue_id'], ['issue.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('issue_ref')
    op.drop_index('ix_source_record_batch_row', table_name='source_record')
    op.drop_table('source_record')
    op.drop_index('ix_raw_row_batch_row', table_name='raw_row')
    op.drop_table('raw_row')
    op.drop_index(op.f('ix_issue_code'), table_name='issue')
    op.drop_table('issue')
    op.drop_table('import_batch')
    op.drop_index(op.f('ix_asset_asset_key'), table_name='asset')
    op.drop_table('asset')
    op.drop_table('source')
    op.drop_table('reconciliation_run')
