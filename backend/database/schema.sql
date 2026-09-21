-- =============================================================================
-- Vitals Clinical Document Intelligence Platform: PostgreSQL Database Schema
-- Compatible with: Azure Database for PostgreSQL (Flexible Server) and local PostgreSQL
-- =============================================================================

-- Enable UUID extension if supported
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Documents Table: Tracks raw document uploads, blob storage locations, and pipeline status
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    blob_path VARCHAR(500) NOT NULL UNIQUE,
    blob_url TEXT NOT NULL,
    patient_id VARCHAR(100),
    document_type VARCHAR(50) DEFAULT 'unknown',
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded', 
    -- Statuses: 'uploaded', 'processing', 'completed', 'validation_failed', 'error', 'retry_pending'
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Vital Metrics Table: Stores extracted and categorized clinical biomarkers
CREATE TABLE IF NOT EXISTS vital_metrics (
    id SERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    patient_id VARCHAR(100),
    
    -- Blood Pressure Readings
    systolic INT,
    diastolic INT,
    bp_unit VARCHAR(20) DEFAULT 'mmHg',
    bp_category VARCHAR(100), -- Normal, Elevated, Stage 1/2 Hypertension, Crisis
    bp_raw_snippet TEXT,
    
    -- HbA1c Glycemic Readings
    hba1c_value NUMERIC(4, 2),
    hba1c_unit VARCHAR(20) DEFAULT '%',
    hba1c_category VARCHAR(100), -- Normal, Prediabetes, Diabetes
    hba1c_raw_snippet TEXT,
    
    -- AI Metadata & Full JSON extraction payload
    extraction_confidence NUMERIC(3, 2) DEFAULT 1.0,
    raw_extraction JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Validation Logs Table: Audit trail of Business Rules Engine decisions
CREATE TABLE IF NOT EXISTS validation_logs (
    id SERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    overall_valid BOOLEAN NOT NULL,
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    requires_retry BOOLEAN NOT NULL DEFAULT FALSE,
    summary_message TEXT NOT NULL,
    rule_evaluations JSONB NOT NULL, -- Detailed list of all rules tested
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Retry History Table: Tracks manual and automated Logic App retries
CREATE TABLE IF NOT EXISTS retry_history (
    id SERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    attempt_number INT NOT NULL,
    triggered_by VARCHAR(50) NOT NULL, -- 'logic_app_auto', 'clinician_ui', 'api_request'
    previous_status VARCHAR(50) NOT NULL,
    new_status VARCHAR(50) NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_patient_id ON documents(patient_id);
CREATE INDEX IF NOT EXISTS idx_vital_metrics_doc_id ON vital_metrics(document_id);
CREATE INDEX IF NOT EXISTS idx_validation_logs_doc_id ON validation_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_retry_history_doc_id ON retry_history(document_id);

