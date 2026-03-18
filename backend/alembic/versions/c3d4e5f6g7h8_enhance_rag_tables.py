"""Enhance RAG tables: KB retrieval config, per-doc chunk params, processing progress

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-03-17 12:00:00.000000

Adds:
- rag_knowledge_base: retrieval_mode, semantic/keyword weights, default search config
- rag_document: per-doc chunk overrides, processing step/progress tracking
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add retrieval config, per-doc chunking, and progress tracking columns."""
    # --- rag_knowledge_base: retrieval & search defaults ---
    op.add_column('rag_knowledge_base', sa.Column(
        'retrieval_mode', sa.String(32), nullable=False, server_default='hybrid'))
    op.add_column('rag_knowledge_base', sa.Column(
        'semantic_weight', sa.Float(), nullable=False, server_default='0.7'))
    op.add_column('rag_knowledge_base', sa.Column(
        'keyword_weight', sa.Float(), nullable=False, server_default='0.3'))
    op.add_column('rag_knowledge_base', sa.Column(
        'default_top_k', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('rag_knowledge_base', sa.Column(
        'enable_score_threshold', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('rag_knowledge_base', sa.Column(
        'default_score_threshold', sa.Float(), nullable=False, server_default='0.0'))

    # --- rag_document: per-doc chunk parameter overrides ---
    op.add_column('rag_document', sa.Column(
        'chunk_method', sa.String(32), nullable=True))
    op.add_column('rag_document', sa.Column(
        'chunk_size', sa.Integer(), nullable=True))
    op.add_column('rag_document', sa.Column(
        'chunk_overlap', sa.Integer(), nullable=True))
    op.add_column('rag_document', sa.Column(
        'chunk_separator', sa.String(255), nullable=True))

    # --- rag_document: processing progress tracking ---
    op.add_column('rag_document', sa.Column(
        'processing_step', sa.String(32), nullable=True))
    op.add_column('rag_document', sa.Column(
        'parse_progress', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('rag_document', sa.Column(
        'chunk_progress', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('rag_document', sa.Column(
        'embed_progress', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove enhanced RAG columns."""
    # rag_document: progress
    op.drop_column('rag_document', 'embed_progress')
    op.drop_column('rag_document', 'chunk_progress')
    op.drop_column('rag_document', 'parse_progress')
    op.drop_column('rag_document', 'processing_step')

    # rag_document: chunk overrides
    op.drop_column('rag_document', 'chunk_separator')
    op.drop_column('rag_document', 'chunk_overlap')
    op.drop_column('rag_document', 'chunk_size')
    op.drop_column('rag_document', 'chunk_method')

    # rag_knowledge_base: retrieval config
    op.drop_column('rag_knowledge_base', 'default_score_threshold')
    op.drop_column('rag_knowledge_base', 'enable_score_threshold')
    op.drop_column('rag_knowledge_base', 'default_top_k')
    op.drop_column('rag_knowledge_base', 'keyword_weight')
    op.drop_column('rag_knowledge_base', 'semantic_weight')
    op.drop_column('rag_knowledge_base', 'retrieval_mode')
