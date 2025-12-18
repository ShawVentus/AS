-- 添加用户引导完成状态字段
-- 功能：记录用户是否已完成产品引导教程
-- 日期：2025-12-18

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS has_completed_tour BOOLEAN DEFAULT FALSE;

-- 添加注释
COMMENT ON COLUMN profiles.has_completed_tour IS '用户是否已完成产品引导教程';
