-- Migration: Add Email System Tables
-- Created: 2024-12-09
-- Description: Adds tables for email analytics, system logs, report feedback, and extends reports table.

-- 1. Extend reports table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS total_papers_count INT DEFAULT 0;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS recommended_papers_count INT DEFAULT 0;

-- 2. Create email_analytics table
CREATE TABLE IF NOT EXISTS email_analytics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    report_id TEXT REFERENCES reports(id),
    user_id TEXT,
    event_type TEXT NOT NULL, -- 'sent', 'opened', 'clicked'
    event_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

CREATE INDEX IF NOT EXISTS idx_email_analytics_report ON email_analytics(report_id);
CREATE INDEX IF NOT EXISTS idx_email_analytics_event ON email_analytics(event_type);

-- 3. Create system_logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    level TEXT NOT NULL, -- 'INFO', 'WARNING', 'ERROR'
    source TEXT NOT NULL,
    message TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_source ON system_logs(source);

-- 4. Create report_feedback table
CREATE TABLE IF NOT EXISTS report_feedback (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    report_id TEXT REFERENCES reports(id),
    user_id TEXT,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai'),
    UNIQUE(report_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_report_feedback_rating ON report_feedback(rating);
