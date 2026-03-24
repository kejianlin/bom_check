#!/bin/bash
###############################################################################
# 数据库恢复脚本
# 用途：从备份恢复PLM同步数据库
# 使用：bash restore_database.sh <backup_file>
###############################################################################

set -e

# 检查参数
if [ $# -eq 0 ]; then
    echo "使用方法: bash restore_database.sh <backup_file>"
    echo "示例: bash restore_database.sh /opt/bom_check/backup/plm_sync_db_20260306_020000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

# 从环境变量读取数据库配置
source /opt/bom_check/.env

echo "警告: 此操作将覆盖现有数据库!"
read -p "确认恢复数据库 $SYNC_DB_NAME? (yes/no): " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "操作已取消"
    exit 0
fi

echo "开始恢复数据库: $SYNC_DB_NAME"
echo "备份文件: $BACKUP_FILE"

# 执行恢复
if [ "$SYNC_DB_TYPE" == "mysql" ]; then
    gunzip < $BACKUP_FILE | mysql -h$SYNC_DB_HOST -P$SYNC_DB_PORT \
        -u$SYNC_DB_USER -p$SYNC_DB_PASSWORD $SYNC_DB_NAME
        
elif [ "$SYNC_DB_TYPE" == "postgresql" ]; then
    PGPASSWORD=$SYNC_DB_PASSWORD gunzip < $BACKUP_FILE | psql -h $SYNC_DB_HOST \
        -p $SYNC_DB_PORT -U $SYNC_DB_USER -d $SYNC_DB_NAME
else
    echo "不支持的数据库类型: $SYNC_DB_TYPE"
    exit 1
fi

# 检查恢复是否成功
if [ $? -eq 0 ]; then
    echo "恢复成功"
else
    echo "恢复失败"
    exit 1
fi
