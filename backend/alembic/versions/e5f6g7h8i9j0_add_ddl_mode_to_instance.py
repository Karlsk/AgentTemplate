"""Add ddl_mode column to nl2sql_instance

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-18 12:00:00.000000

Adds ddl_mode column (VARCHAR(16), NOT NULL, DEFAULT 'full') to
nl2sql_instance table for configuring DDL embedding strategy.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nl2sql_instance',
        sa.Column('ddl_mode', sa.String(16),
                  nullable=False, server_default='full'),
    )


def downgrade() -> None:
    op.drop_column('nl2sql_instance', 'ddl_mode')
