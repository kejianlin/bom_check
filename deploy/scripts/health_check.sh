#!/bin/bash
###############################################################################
# 健康检查脚本
# 用途：检查BOM系统各组件运行状态
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  BOM检查系统健康检查"
echo "=========================================="
echo ""

# 检查API服务
echo -n "API服务状态: "
if systemctl is-active --quiet bom-api.service; then
    echo -e "${GREEN}运行中${NC}"
else
    echo -e "${RED}已停止${NC}"
fi

# 检查API端点
echo -n "API健康检查: "
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}正常${NC}"
else
    echo -e "${RED}异常${NC}"
fi

# 检查同步定时器
echo -n "同步定时器: "
if systemctl is-active --quiet bom-sync.timer; then
    echo -e "${GREEN}已启用${NC}"
    NEXT_RUN=$(systemctl status bom-sync.timer | grep "Trigger:" | awk '{print $2, $3, $4, $5}')
    echo "  下次运行: $NEXT_RUN"
else
    echo -e "${RED}未启用${NC}"
fi

# 检查数据库连接
echo -n "数据库连接: "
source /opt/bom_check/.env
if [ "$SYNC_DB_TYPE" == "mysql" ]; then
    if mysqladmin -h$SYNC_DB_HOST -P$SYNC_DB_PORT -u$SYNC_DB_USER -p$SYNC_DB_PASSWORD ping > /dev/null 2>&1; then
        echo -e "${GREEN}正常${NC}"
    else
        echo -e "${RED}失败${NC}"
    fi
elif [ "$SYNC_DB_TYPE" == "postgresql" ]; then
    if PGPASSWORD=$SYNC_DB_PASSWORD psql -h $SYNC_DB_HOST -p $SYNC_DB_PORT -U $SYNC_DB_USER -d $SYNC_DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}正常${NC}"
    else
        echo -e "${RED}失败${NC}"
    fi
fi

# 检查磁盘空间
echo ""
echo "磁盘使用情况:"
df -h /opt/bom_check | tail -n 1 | awk '{print "  使用: " $5 " (" $3 " / " $2 ")"}'

# 检查日志大小
echo ""
echo "日志文件大小:"
du -sh /opt/bom_check/logs 2>/dev/null | awk '{print "  " $1}'

# 最近的同步记录
echo ""
echo "最近的同步记录:"
if [ -f /opt/bom_check/logs/sync_service.log ]; then
    tail -n 5 /opt/bom_check/logs/sync_service.log | grep -E "(成功|失败|完成)" | tail -n 3
else
    echo "  无同步日志"
fi

echo ""
echo "=========================================="
