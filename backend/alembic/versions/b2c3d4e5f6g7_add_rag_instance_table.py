"""Add rag_instances table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('rag_instances',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('workspace_id', sa.BigInteger(), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('collection_name', sa.String(length=255), nullable=False),
                    sa.Column('embedding_model_id', sa.Integer(), nullable=False),
                    sa.Column('config', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('collection_name')
                    )
    op.create_index(op.f('ix_rag_instances_workspace_id'), 'rag_instances', ['workspace_id'], unique=False)
    # 建立唯一索引 (id, workspace_id) 为了满足 1.3 需求，虽然主键已经唯一，但在多租户场景下这种复合索引常用于快速定位和逻辑校验
    op.create_index('ix_rag_instance_id_workspace', 'rag_instances', ['id', 'workspace_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_rag_instance_id_workspace', table_name='rag_instances')
    op.drop_index(op.f('ix_rag_instances_workspace_id'), table_name='rag_instances')
    op.drop_table('rag_instances')
