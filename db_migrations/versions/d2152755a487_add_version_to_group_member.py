"""Начальная миграция: создание таблиц group_member и deleted_message

Revision ID: d2152755a487
Revises:
Create Date: 2026-03-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd2152755a487'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'group_member',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('group_id', sa.BigInteger(), nullable=False),
        sa.Column('is_captcha_passed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_group_member_user_id', 'group_member', ['user_id'])
    op.create_index('ix_group_member_group_id', 'group_member', ['group_id'])

    op.create_table(
        'deleted_message',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('group_id', sa.BigInteger(), nullable=False),
        sa.Column('message_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.String(4096), nullable=True),
        sa.Column('reason', sa.String(64), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deleted_message_user_id', 'deleted_message', ['user_id'])
    op.create_index('ix_deleted_message_group_id', 'deleted_message', ['group_id'])


def downgrade() -> None:
    op.drop_index('ix_deleted_message_group_id', table_name='deleted_message')
    op.drop_index('ix_deleted_message_user_id', table_name='deleted_message')
    op.drop_table('deleted_message')

    op.drop_index('ix_group_member_group_id', table_name='group_member')
    op.drop_index('ix_group_member_user_id', table_name='group_member')
    op.drop_table('group_member')
