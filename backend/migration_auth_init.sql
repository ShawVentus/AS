-- 身份验证系统初始化脚本
-- 目标: 切换到 Supabase Auth，清理旧的 public.users，建立自动 Profile 创建机制

-- 1. 清理旧的外键约束 (引用 public.users 的表)
ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_user_id_fkey;
ALTER TABLE user_paper_states DROP CONSTRAINT IF EXISTS user_paper_states_user_id_fkey;
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_user_id_fkey; -- 如果有的话

-- 2. 删除旧的 public.users 表
DROP TABLE IF EXISTS public.users;

-- 3. 确保 user_id 字段类型与 auth.users.id (uuid) 兼容
-- 如果之前是 text，建议转为 uuid (需要确保现有数据也是 uuid 格式，否则会报错)
-- 这里假设是新项目或数据可重置。如果转换失败，请手动处理数据。
-- ALTER TABLE profiles ALTER COLUMN user_id TYPE uuid USING user_id::uuid;
-- ALTER TABLE reports ALTER COLUMN user_id TYPE uuid USING user_id::uuid;
-- ALTER TABLE user_paper_states ALTER COLUMN user_id TYPE uuid USING user_id::uuid;

-- 暂保持 text 以兼容现有代码，但建议未来迁移到 uuid。
-- Supabase Auth ID 是 UUID，但在 public 表中存为 text 是兼容的。

-- 4. 创建自动创建 Profile 的触发器函数
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (user_id, info, focus, context, memory)
  VALUES (
    NEW.id::text, -- 将 UUID 转为 text 存入
    jsonb_build_object('email', NEW.email),
    '{}'::jsonb,
    '{}'::jsonb,
    '{}'::jsonb
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. 绑定触发器到 auth.users
-- 先删除旧的(如果存在)以避免重复
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 6. 更新 RLS 策略 (确保引用 auth.uid())

-- Profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid()::text = user_id);

-- User Paper States
ALTER TABLE user_paper_states ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view their own paper states" ON user_paper_states;
CREATE POLICY "Users can view their own paper states" ON user_paper_states FOR SELECT USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can insert their own paper states" ON user_paper_states;
CREATE POLICY "Users can insert their own paper states" ON user_paper_states FOR INSERT WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can update their own paper states" ON user_paper_states;
CREATE POLICY "Users can update their own paper states" ON user_paper_states FOR UPDATE USING (auth.uid()::text = user_id);

-- Reports
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view their own reports" ON reports;
CREATE POLICY "Users can view their own reports" ON reports FOR SELECT USING (auth.uid()::text = user_id);

-- 7. 补充外键约束 (可选，指向 auth.users)
-- 注意: 只有当 user_id 是 uuid 类型时才能直接引用 auth.users(id)
-- 如果 user_id 是 text，无法建立直接 FK 到 uuid 列。
-- 建议: 依赖 RLS 和 Trigger 保证一致性，或者将 user_id 改为 uuid 类型。
