-- PLM同步数据库初始化脚本
-- 用途：创建数据库和用户，设置权限

-- 创建数据库
CREATE DATABASE IF NOT EXISTS plm_sync_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'sync_user'@'localhost' IDENTIFIED BY 'sync_password';
CREATE USER IF NOT EXISTS 'sync_user'@'%' IDENTIFIED BY 'sync_password';

-- 授予权限
GRANT ALL PRIVILEGES ON plm_sync_db.* TO 'sync_user'@'localhost';
GRANT ALL PRIVILEGES ON plm_sync_db.* TO 'sync_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 使用数据库
USE plm_sync_db;

-- 创建同步日志表
CREATE TABLE IF NOT EXISTS sync_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    sync_mode VARCHAR(20) NOT NULL COMMENT 'full/incremental',
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    records_count INT DEFAULT 0,
    status VARCHAR(20) NOT NULL COMMENT 'success/failed/running',
    error_message TEXT,
    duration_seconds INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_table_name (table_name),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据同步日志表';

-- 创建同步配置表
CREATE TABLE IF NOT EXISTS sync_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT TRUE,
    sync_mode VARCHAR(20) DEFAULT 'incremental',
    last_sync_time DATETIME,
    last_sync_status VARCHAR(20),
    sync_interval_hours INT DEFAULT 24,
    batch_size INT DEFAULT 1000,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同步配置表';

-- 插入默认配置
INSERT INTO sync_config (table_name, enabled, sync_mode, notes) VALUES
('CPCBOM', TRUE, 'incremental', 'BOM主表'),
('CPCBOMD', TRUE, 'incremental', 'BOM明细表'),
('CPCITEM', TRUE, 'incremental', '物料表')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 创建数据版本表（用于增量同步）
CREATE TABLE IF NOT EXISTS data_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    version_number INT NOT NULL,
    record_count INT DEFAULT 0,
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_table_version (table_name, version_number),
    INDEX idx_table_name (table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据版本表';

-- 显示创建的表
SHOW TABLES;

SELECT 'PLM同步数据库初始化完成！' AS message;
