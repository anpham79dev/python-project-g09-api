"""Add PBAC roles, permissions, role_permissions, audit_logs tables

Revision ID: a1b2c3d4e5f6
Revises: 80ead1f52855
Create Date: 2026-08-17 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone, timedelta
from app.core.rbac_config import ALL_PERMISSIONS, SYSTEM_ROLES_CONFIG

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '80ead1f52855'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_permissions_code'), 'permissions', ['code'], unique=True)
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'], unique=False)
    op.create_index(op.f('ix_permissions_module'), 'permissions', ['module'], unique=False)

    # 2. Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('permissions_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_code'), 'roles', ['code'], unique=True)
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)

    # 3. Create role_permissions join table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.String(length=50), nullable=False),
        sa.Column('permission_id', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # 4. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('user_name', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=50), nullable=False),
        sa.Column('target_name', sa.String(length=100), nullable=False),
        sa.Column('changes_summary', sa.Text(), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_id'), 'audit_logs', ['target_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    # 5. Add role_id column to users table
    op.add_column('users', sa.Column('role_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)
    op.create_foreign_key('fk_users_role_id', 'users', 'roles', ['role_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_users_role_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_column('users', 'role_id')
    op.drop_table('audit_logs')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
