-- Add note column to user_paper_states table
ALTER TABLE user_paper_states ADD COLUMN IF NOT EXISTS note TEXT;
