-- ==========================================
-- 升级脚本: 为 MySQL 用户表新增飞书 OAuth 字段
-- 在执行前确保已备份数据
-- ==========================================

ALTER TABLE `users`
  ADD COLUMN `feishu_open_id` VARCHAR(64) NULL AFTER `linux_do_username`,
  ADD COLUMN `feishu_union_id` VARCHAR(64) NULL AFTER `feishu_open_id`;

ALTER TABLE `users`
  ADD UNIQUE KEY `uk_feishu_open_id` (`feishu_open_id`);
