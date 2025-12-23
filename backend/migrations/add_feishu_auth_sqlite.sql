-- ==========================================
-- 升级脚本: 为 SQLite 用户表新增飞书 OAuth 字段
-- 说明: SQLite 不支持 IF NOT EXISTS，重复执行会提示列已存在，可忽略
-- ==========================================

ALTER TABLE users ADD COLUMN feishu_open_id VARCHAR(64);
ALTER TABLE users ADD COLUMN feishu_union_id VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS uk_feishu_open_id ON users(feishu_open_id);
