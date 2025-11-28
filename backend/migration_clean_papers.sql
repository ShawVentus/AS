-- 数据库清理脚本
-- 移除冗余字段，保持 papers 表只存储 RawPaperMetadata + details

-- 1. 移除不再使用的字段
ALTER TABLE papers DROP COLUMN IF EXISTS tldr;
ALTER TABLE papers DROP COLUMN IF EXISTS suggestion;
ALTER TABLE papers DROP COLUMN IF EXISTS tags;
ALTER TABLE papers DROP COLUMN IF EXISTS "citationCount";
ALTER TABLE papers DROP COLUMN IF EXISTS year;
ALTER TABLE papers DROP COLUMN IF EXISTS "isLiked";
ALTER TABLE papers DROP COLUMN IF EXISTS "whyThisPaper";

-- 2. 修改 category 字段类型为 text[] (存储所有分类)
-- 如果当前是 text 类型，将其转换为数组
ALTER TABLE papers 
ALTER COLUMN category TYPE text[] 
USING CASE 
    WHEN category IS NULL THEN '{}'::text[]
    ELSE ARRAY[category] 
END;

-- 3. 确认最终 Schema
-- papers 表应包含以下字段:
-- - id (PK)
-- - title, authors, published_date, category, abstract, comment, links (RawPaperMetadata)
-- - status ('pending' / 'completed' / 'failed')
-- - details (JSONB, 存储 PaperAnalysis)
-- - created_at
