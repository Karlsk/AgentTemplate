"""Add mcp_server table

Revision ID: a1b2c3d4e5f6
Revises: 75a7c943063f
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '75a7c943063f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('mcp_server',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('name', sa.String(255), nullable=False),
                    sa.Column('mcp_url', sa.String(255), nullable=False),
                    sa.Column('transport', sa.String(255), nullable=False),
                    sa.Column('config', sa.Text(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('mcp_server')
