#!/bin/bash
###############################################################################
# 数据库备份脚本
# 用途：备份PLM同步数据库
###############################################################################

set -e

# 配置
BACKUP_DIR="/opt/bom_check/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

# 从环境变量读取数据库配置
source /opt/bom_check/.env

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份文件名
BACKUP_FILE="$BACKUP_DIR/plm_sync_db_$TIMESTAMP.sql.gz"

echo "开始备份数据库: $SYNC_DB_NAME"
echo "备份文件: $BACKUP_FILE"

# 执行备份
if [ "$SYNC_DB_TYPE" == "mysql" ]; then
    mysqldump -h$SYNC_DB_HOST -P$SYNC_DB_PORT -u$SYNC_DB_USER -p$SYNC_DB_PASSWORD \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        $SYNC_DB_NAME | gzip > $BACKUP_FILE
        
elif [ "$SYNC_DB_TYPE" == "postgresql" ]; then
    PGPASSWORD=$SYNC_DB_PASSWORD pg_dump -h $SYNC_DB_HOST -p $SYNC_DB_PORT \
        -U $SYNC_DB_USER -d $SYNC_DB_NAME | gzip > $BACKUP_FILE
else
    echo "不支持的数据库类型: $SYNC_DB_TYPE"
    exit 1
fi

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "备份成功: $BACKUP_FILE"
    echo "备份大小: $(du -h $BACKUP_FILE | cut -f1)"
else
    echo "备份失败"
    exit 1
fi

# 清理旧备份
echo "清理 $RETENTION_DAYS 天前的旧备份..."
find $BACKUP_DIR -name "plm_sync_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "备份完成"
