-- Add progress column to workflow_steps table
ALTER TABLE workflow_steps 
ADD COLUMN IF NOT EXISTS progress JSONB DEFAULT NULL;

-- Comment on column
COMMENT ON COLUMN workflow_steps.progress IS 'Step execution progress: {current: int, total: int, message: str}';
