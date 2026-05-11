-- APES PostgreSQL schema.
-- This file runs automatically when the postgres Docker container starts
-- for the first time with an empty data directory.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT UNIQUE NOT NULL,
    shop_url TEXT NOT NULL,
    store_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'complete', 'failed')),
    before_score INTEGER,
    after_score INTEGER,
    score_delta INTEGER GENERATED ALWAYS AS (after_score - before_score) STORED,
    total_queries INTEGER DEFAULT 20,
    failed_queries INTEGER DEFAULT 0,
    high_impact_fixes INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS store_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    store_data JSONB NOT NULL,
    gaps_detected JSONB NOT NULL DEFAULT '[]',
    crawl_coverage JSONB NOT NULL DEFAULT '{}',
    product_count INTEGER DEFAULT 0,
    has_policies BOOLEAN DEFAULT FALSE,
    has_faqs BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS persona_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    query_id TEXT NOT NULL,
    persona TEXT NOT NULL,
    category TEXT,
    query TEXT NOT NULL,
    intent TEXT,
    dimension TEXT NOT NULL,
    difficulty TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(audit_id, query_id)
);

CREATE TABLE IF NOT EXISTS simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    query_id TEXT NOT NULL,
    persona TEXT NOT NULL,
    query TEXT NOT NULL,
    dimension TEXT NOT NULL,
    response TEXT,
    classification TEXT CHECK (classification IN ('CONFIDENT_CORRECT', 'VAGUE', 'REFUSED', 'HALLUCINATED')),
    confidence FLOAT,
    severity TEXT CHECK (severity IN ('high', 'medium', 'low')),
    hedging_detected BOOLEAN DEFAULT FALSE,
    refusal_detected BOOLEAN DEFAULT FALSE,
    is_grounded BOOLEAN DEFAULT TRUE,
    ungrounded_claims JSONB DEFAULT '[]',
    fixed_context BOOLEAN DEFAULT FALSE,
    after_response TEXT,
    after_classification TEXT CHECK (after_classification IN ('CONFIDENT_CORRECT', 'VAGUE', 'REFUSED', 'HALLUCINATED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(audit_id, query_id)
);

CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    query_id TEXT NOT NULL,
    gap_type TEXT NOT NULL CHECK (gap_type IN ('missing_field', 'ambiguous_content', 'contradictory_data', 'no_reviews', 'policy_gap')),
    specific_issue TEXT NOT NULL,
    location TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
    impact_on_conversion TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(audit_id, query_id)
);

CREATE TABLE IF NOT EXISTS fixes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    query_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    original_content TEXT,
    improved_content TEXT,
    changes_made JSONB DEFAULT '[]',
    confidence_improvement_reason TEXT,
    impact_points INTEGER DEFAULT 0,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(audit_id, query_id)
);

CREATE TABLE IF NOT EXISTS score_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE UNIQUE,
    before_score INTEGER NOT NULL,
    after_score INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    before_dimensions JSONB NOT NULL,
    after_dimensions JSONB NOT NULL,
    action_plan JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audits_shop_url ON audits(shop_url);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);
CREATE INDEX IF NOT EXISTS idx_audits_created ON audits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_store_ctx_audit ON store_contexts(audit_id);
CREATE INDEX IF NOT EXISTS idx_queries_audit ON persona_queries(audit_id);
CREATE INDEX IF NOT EXISTS idx_sims_audit ON simulations(audit_id);
CREATE INDEX IF NOT EXISTS idx_sims_classification ON simulations(audit_id, classification);
CREATE INDEX IF NOT EXISTS idx_findings_audit ON findings(audit_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(audit_id, severity);
CREATE INDEX IF NOT EXISTS idx_fixes_audit ON fixes(audit_id);
CREATE INDEX IF NOT EXISTS idx_fixes_applied ON fixes(audit_id, applied);
CREATE INDEX IF NOT EXISTS idx_scores_audit ON score_reports(audit_id);
