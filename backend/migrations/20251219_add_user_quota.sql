-- 用户额度系统数据库迁移脚本
-- 功能：
-- 1. 为 profiles 表增加 remaining_quota 字段，记录用户剩余报告生成次数。
-- 2. 创建 quota_logs 表，用于记录额度变动的审计日志。

-- 1. 为 profiles 表增加 remaining_quota 字段
-- 默认值为 1，表示新用户或现有用户初始赠送 1 个额度。
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS remaining_quota INTEGER DEFAULT 1;

-- 2. 创建额度变动日志表
-- 用于追踪额度的来源和去向（如：生成报告扣减、充值增加、系统赠送等）。
CREATE TABLE IF NOT EXISTS quota_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    change_amount INTEGER NOT NULL, -- 变动数量：正数表示增加，负数表示扣减
    reason TEXT NOT NULL, -- 变动原因：'report_generated' (生成报告), 'recharge' (充值), 'admin_grant' (管理员发放), 'system_gift' (系统赠送)
    related_report_id TEXT, -- 可选：关联的报告 ID（如果是因生成报告扣减）
    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 为常用查询字段创建索引，优化性能
CREATE INDEX IF NOT EXISTS idx_quota_logs_user ON quota_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_quota_logs_created ON quota_logs(created_at);

-- 注释说明
COMMENT ON COLUMN profiles.remaining_quota IS '用户剩余报告生成额度';
COMMENT ON TABLE quota_logs IS '用户额度变动审计日志表';
