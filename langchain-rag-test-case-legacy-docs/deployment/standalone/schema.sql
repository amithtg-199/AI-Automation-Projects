-- ============================================================================
-- Unified Schema (Merging new LangChain versioning + old n8n tracking tables)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ────────────────────────────────────────────────────────────────────────────
-- 1. Projects & Versioning (NEW LangChain Schema)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    project_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(255) UNIQUE NOT NULL,
    version      TEXT,
    description  TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS versions (
    version_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    version_number      INT NOT NULL,
    project_snapshot_id UUID NOT NULL,
    is_latest           BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ────────────────────────────────────────────────────────────────────────────
-- 2. Documents & Chunks (NEW LangChain Schema)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    document_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    version_id          UUID REFERENCES versions(version_id) ON DELETE CASCADE,
    project_snapshot_id UUID NOT NULL,
    file_name           VARCHAR(512) NOT NULL,
    document_type       VARCHAR(50),
    metadata            JSONB,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parent_chunks (
    parent_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    project_id          UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    version_id          UUID REFERENCES versions(version_id) ON DELETE CASCADE,
    project_snapshot_id UUID NOT NULL,
    chunk_index         INT NOT NULL,
    section_name        VARCHAR(255),
    content             TEXT NOT NULL,
    token_count         INT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id       TEXT PRIMARY KEY,                        -- deterministic hash id
    parent_id      UUID REFERENCES parent_chunks(parent_id) ON DELETE CASCADE,
    project_name   TEXT NOT NULL,
    document_type  TEXT,                                    
    section        TEXT,                                    
    version        TEXT DEFAULT '1.0',
    chunk_index    INTEGER,
    char_count     INTEGER,
    created_at     TIMESTAMP DEFAULT NOW()
);



-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_projects_name              ON projects(project_name);
CREATE INDEX IF NOT EXISTS idx_versions_project           ON versions(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_project          ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_version          ON documents(version_id);
CREATE INDEX IF NOT EXISTS idx_parent_chunks_document     ON parent_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_parent     ON document_chunks(parent_id);
