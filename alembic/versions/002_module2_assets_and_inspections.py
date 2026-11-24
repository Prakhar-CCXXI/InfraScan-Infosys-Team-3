"""Module 2: Infrastructure Assets & Inspections schema migration.

Revision ID: 002_module2_assets_and_inspections
Revises: 001_initial_rbac_schema
Create Date: 2026-11-20 08:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_module2_assets_and_inspections'
down_revision: Union[str, None] = '001_initial_rbac_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create infrastructure_assets table
    op.create_table(
        'infrastructure_assets',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('asset_name', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=100), nullable=False),
        sa.Column('location', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('construction_year', sa.Integer(), nullable=True),
        sa.Column('material_type', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('inspection_frequency', sa.Integer(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_infrastructure_assets_asset_name', 'infrastructure_assets', ['asset_name'])
    op.create_index('ix_infrastructure_assets_asset_type', 'infrastructure_assets', ['asset_type'])
    op.create_index('ix_infrastructure_assets_department', 'infrastructure_assets', ['department'])
    op.create_index('ix_infrastructure_assets_is_archived', 'infrastructure_assets', ['is_archived'])

    # 2. Create inspections table
    op.create_table(
        'inspections',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('asset_id', sa.Uuid(as_uuid=True), sa.ForeignKey('infrastructure_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('inspector_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('inspection_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='CREATED'),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_inspections_asset_id', 'inspections', ['asset_id'])
    op.create_index('ix_inspections_inspector_id', 'inspections', ['inspector_id'])
    op.create_index('ix_inspections_status', 'inspections', ['status'])
    op.create_index('ix_inspections_inspection_date', 'inspections', ['inspection_date'])


def downgrade() -> None:
    op.drop_table('inspections')
    op.drop_table('infrastructure_assets')
