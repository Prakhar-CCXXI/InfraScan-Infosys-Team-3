"""Initial RBAC and Audit Logging schema migration for Module 1.

Revision ID: 001_initial_rbac_schema
Revises: 
Create Date: 2026-11-20 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_rbac_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

USER_ROLES = (
    'CIVIL_ENGINEER',
    'INFRASTRUCTURE_INSPECTOR',
    'MAINTENANCE_ENGINEER',
    'INFRASTRUCTURE_MANAGER',
    'ADMIN'
)


def upgrade() -> None:
    # 1. Ensure pgcrypto extension exists for UUID generation on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";")

    # 2. Define user_role enum
    user_role_enum = sa.Enum(
        *USER_ROLES,
        name='user_role',
        create_type=False,
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE user_role AS ENUM (
                    'CIVIL_ENGINEER',
                    'INFRASTRUCTURE_INSPECTOR',
                    'MAINTENANCE_ENGINEER',
                    'INFRASTRUCTURE_MANAGER',
                    'ADMIN'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )

    # 3. Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, server_default='INFRASTRUCTURE_INSPECTOR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])

    # 4. Create 'audit_logs' table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('users')
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS user_role CASCADE;")
