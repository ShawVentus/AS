-- 支付交易记录表
-- 功能：记录用户通过玻尔平台购买研报次数的每笔交易
-- 创建时间：2025-12-20
-- 
-- 表设计说明：
--   - user_id: 外键关联 profiles 表，确保用户必须先初始化
--   - biz_no: 本地生成的14位唯一业务流水号，防止重复扣款
--   - out_biz_no/request_id: 玻尔平台返回的交易凭证，用于对账
--   - event_value/quota_amount: 分别记录消费的光子数和获得的次数

-- 1. 创建交易记录表
CREATE TABLE IF NOT EXISTS payment_transactions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES profiles(user_id),  -- 外键关联 profiles 表
    biz_no BIGINT UNIQUE NOT NULL,                       -- 本地生成的14位业务流水号
    out_biz_no TEXT,                                      -- 玻尔平台返回的交易流水号
    request_id BIGINT,                                    -- 玻尔平台返回的请求ID
    event_value INT NOT NULL,                             -- 消费的光子数量
    quota_amount INT NOT NULL,                            -- 购买的次数
    sku_id INT DEFAULT 10020,                             -- 商品ID（固定值）
    status TEXT DEFAULT 'success',                        -- 状态：success / failed
    error_message TEXT,                                   -- 失败原因（如有）
    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
);

-- 2. 创建索引（优化常用查询）
CREATE INDEX IF NOT EXISTS idx_payment_user ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_created ON payment_transactions(created_at);

-- 3. 添加表和字段注释
COMMENT ON TABLE payment_transactions IS '用户购买研报次数的交易记录表';
COMMENT ON COLUMN payment_transactions.user_id IS '用户ID，关联 profiles 表';
COMMENT ON COLUMN payment_transactions.biz_no IS '本地生成的14位业务流水号（时间戳+4位随机数）';
COMMENT ON COLUMN payment_transactions.out_biz_no IS '玻尔平台返回的交易流水号';
COMMENT ON COLUMN payment_transactions.event_value IS '消费的光子数量（100/400/1200）';
COMMENT ON COLUMN payment_transactions.quota_amount IS '购买的研报生成次数（1/5/20）';
COMMENT ON COLUMN payment_transactions.status IS '交易状态：success 成功 / failed 失败';
