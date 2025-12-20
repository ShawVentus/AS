-- ================================================================
-- 迁移脚本: 为用户画像增加"接收每日报告"开关字段
-- 版本: 20251219_add_receive_email
-- 作者: Antigravity
-- 日期: 2025-12-19
-- 主要功能：
-- 1. 为 profiles 表增加 receive_email 字段，控制自动报告推送。
-- 2. 为现有用户初始化为 TRUE，确保向后兼容。
-- ================================================================

-- 1. 为 profiles 表增加 receive_email 字段
-- 说明：此字段控制用户是否接收每日自动生成的报告邮件
-- 默认值设为 FALSE，新注册用户需要手动开启
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS receive_email BOOLEAN DEFAULT FALSE;

-- 2. 为现有用户设置默认值为 TRUE（向后兼容）
-- 说明：避免迁移后老用户突然停止接收报告，保持原有行为
-- 我们只更新那些字段目前为 NULL 的记录
UPDATE profiles 
SET receive_email = TRUE 
WHERE receive_email IS NULL;

-- 3. 验证迁移结果
-- 说明：检查字段是否成功添加，以及老用户默认值是否正确
-- 打印统计信息以便确认
DO $$
DECLARE
    total_users INTEGER;
    enabled_count INTEGER;
    disabled_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_users FROM profiles;
    SELECT COUNT(*) INTO enabled_count FROM profiles WHERE receive_email = TRUE;
    SELECT COUNT(*) INTO disabled_count FROM profiles WHERE receive_email = FALSE;
    
    RAISE NOTICE '迁移完成统计:';
    RAISE NOTICE '总用户数: %', total_users;
    RAISE NOTICE '已开启报告用户数: %', enabled_count;
    RAISE NOTICE '已关闭报告用户数: %', disabled_count;
END $$;
