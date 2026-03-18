"""Add NL2SQL tables: db_config, instance, training_data, schema_meta

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-17 20:00:00.000000

Adds:
- nl2sql_db_config: database connection configurations
- nl2sql_instance: NL2SQL instances linked to DB configs
- nl2sql_training_data: DDL/SQL/Doc training data metadata
- nl2sql_schema_meta: synced schema metadata (tables + columns)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create NL2SQL tables."""
    # --- nl2sql_db_config ---
    op.create_table(
        'nl2sql_db_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('db_type', sa.String(32), nullable=False),
        sa.Column('host', sa.String(512), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('database_name', sa.String(255), nullable=False),
        sa.Column('schema_name', sa.String(255), nullable=True),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('encrypted_password', sa.Text(), nullable=False),
        sa.Column('extra_params', sa.Text(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_nl2sql_db_config_workspace_id',
                    'nl2sql_db_config', ['workspace_id'])

    # --- nl2sql_instance ---
    op.create_table(
        'nl2sql_instance',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('db_config_id', sa.Integer(), nullable=False),
        sa.Column('embedding_model_id', sa.Integer(), nullable=True),
        sa.Column('ddl_count', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('sql_count', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('doc_count', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_nl2sql_instance_workspace_id',
                    'nl2sql_instance', ['workspace_id'])
    op.create_index('ix_nl2sql_instance_db_config_id',
                    'nl2sql_instance', ['db_config_id'])

    # --- nl2sql_training_data ---
    op.create_table(
        'nl2sql_training_data',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('data_type', sa.String(16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('sql_text', sa.Text(), nullable=True),
        sa.Column('table_name', sa.String(255), nullable=True),
        sa.Column('source', sa.String(32), nullable=False,
                  server_default='manual'),
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_nl2sql_td_instance_id',
                    'nl2sql_training_data', ['instance_id'])
    op.create_index('ix_nl2sql_td_workspace_id',
                    'nl2sql_training_data', ['workspace_id'])
    op.create_index('ix_nl2sql_td_data_type',
                    'nl2sql_training_data', ['data_type'])

    # --- nl2sql_schema_meta ---
    op.create_table(
        'nl2sql_schema_meta',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('db_config_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('table_schema', sa.String(255), nullable=True),
        sa.Column('table_name', sa.String(255), nullable=False),
        sa.Column('table_comment', sa.Text(), nullable=True),
        sa.Column('column_name', sa.String(255), nullable=True),
        sa.Column('column_type', sa.String(128), nullable=True),
        sa.Column('column_comment', sa.Text(), nullable=True),
        sa.Column('is_primary_key', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        sa.Column('is_nullable', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
    )
    op.create_index('ix_nl2sql_sm_instance_id',
                    'nl2sql_schema_meta', ['instance_id'])
    op.create_index('ix_nl2sql_sm_db_config_id',
                    'nl2sql_schema_meta', ['db_config_id'])


def downgrade() -> None:
    """Drop NL2SQL tables."""
    op.drop_table('nl2sql_schema_meta')
    op.drop_table('nl2sql_training_data')
    op.drop_table('nl2sql_instance')
    op.drop_table('nl2sql_db_config')
