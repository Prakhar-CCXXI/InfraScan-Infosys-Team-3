-- ============================================================================
-- Project: InfraScan - Infosys Project
-- Database Architecture: PostgreSQL DDL Initialization Script
-- ============================================================================

-- Extensions for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- Clean up existing objects (if re-running)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS images CASCADE;
DROP TABLE IF EXISTS inspections CASCADE;
DROP TABLE IF EXISTS infrastructure_assets CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;

-- ----------------------------------------------------------------------------
-- Custom ENUM Types
-- ----------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM (
    'CIVIL_ENGINEER',
    'INFRASTRUCTURE_INSPECTOR',
    'MAINTENANCE_ENGINEER',
    'INFRASTRUCTURE_MANAGER',
    'ADMIN'
);

-- ----------------------------------------------------------------------------
-- Table Definitions (In Strict Dependency Order)
-- ----------------------------------------------------------------------------

-- TABLE: users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'INFRASTRUCTURE_INSPECTOR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE: infrastructure_assets
CREATE TABLE infrastructure_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(100) NOT NULL,
    location TEXT NOT NULL,
    latitude DOUBLE PRECISION CHECK (latitude >= -90.0 AND latitude <= 90.0),
    longitude DOUBLE PRECISION CHECK (longitude >= -180.0 AND longitude <= 180.0),
    construction_year INTEGER CHECK (construction_year >= 1800),
    material_type VARCHAR(100),
    department VARCHAR(100),
    inspection_frequency INTEGER CHECK (inspection_frequency > 0),
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE: inspections
CREATE TABLE inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL,
    inspector_id UUID,
    inspection_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    remarks TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inspections_asset 
        FOREIGN KEY (asset_id) 
        REFERENCES infrastructure_assets(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,

    CONSTRAINT fk_inspections_inspector 
        FOREIGN KEY (inspector_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE,

    CONSTRAINT chk_inspection_status CHECK (
        status IN (
            'CREATED',
            'ASSIGNED',
            'IN_PROGRESS',
            'IMAGE_UPLOADED',
            'ANALYSIS_PENDING',
            'COMPLETED',
            'REVIEW_REQUIRED'
        )
    )
);

-- TABLE: images
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL,
    uploaded_by UUID,
    file_name VARCHAR(255) NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    file_format VARCHAR(20),
    file_size BIGINT CHECK (file_size > 0),
    width INTEGER CHECK (width > 0),
    height INTEGER CHECK (height > 0),
    image_hash VARCHAR(64),
    quality_status VARCHAR(50) DEFAULT 'PENDING_REVIEW',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_images_inspection 
        FOREIGN KEY (inspection_id) 
        REFERENCES inspections(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,

    CONSTRAINT fk_images_uploader 
        FOREIGN KEY (uploaded_by) 
        REFERENCES users(id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
);

-- TABLE: audit_logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),

    CONSTRAINT fk_audit_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
);

-- ----------------------------------------------------------------------------
-- Indexes
-- ----------------------------------------------------------------------------
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

CREATE INDEX idx_assets_type ON infrastructure_assets(asset_type);
CREATE INDEX idx_assets_department ON infrastructure_assets(department);
CREATE INDEX idx_assets_geo ON infrastructure_assets(latitude, longitude);

CREATE INDEX idx_inspections_asset_date ON inspections(asset_id, inspection_date DESC);
CREATE INDEX idx_inspections_status ON inspections(status);
CREATE INDEX idx_inspections_inspector ON inspections(inspector_id);

CREATE INDEX idx_images_inspection_id ON images(inspection_id);
CREATE INDEX idx_images_uploaded_by ON images(uploaded_by);
CREATE INDEX idx_images_hash ON images(image_hash);

CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
