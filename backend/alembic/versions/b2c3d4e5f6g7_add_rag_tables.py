"""Add RAG tables (knowledge_base, document) and enable pgvector

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-17 00:00:00.000000

Note: chunk / embedding storage is managed by LlamaIndex PGVectorStore
      which auto-creates its own table (data_rag_vectors).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create RAG metadata tables and enable pgvector extension."""
    # pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Knowledge Base
    op.create_table(
        'rag_knowledge_base',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('embedding_model_id', sa.Integer(), nullable=True),
        sa.Column('chunk_method', sa.String(32),
                  nullable=False, server_default='naive'),
        sa.Column('chunk_size', sa.Integer(),
                  nullable=False, server_default='512'),
        sa.Column('chunk_overlap', sa.Integer(),
                  nullable=False, server_default='64'),
        sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('doc_count', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('chunk_count', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rag_kb_workspace_id',
                    'rag_knowledge_base', ['workspace_id'])

    # Document
    op.create_table(
        'rag_document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('kb_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('chunk_count', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_msg', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rag_doc_kb_id', 'rag_document', ['kb_id'])
    op.create_index('ix_rag_doc_workspace_id',
                    'rag_document', ['workspace_id'])


def downgrade() -> None:
    """Drop RAG metadata tables."""
    op.drop_table('rag_document')
    op.drop_table('rag_knowledge_base')
