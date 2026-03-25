#!/bin/bash
# BOM Check 项目增量上传脚本 (适用于 Git Bash / WSL)
# 使用方法: ./upload_changes.sh

set -e

SERVER_HOST="119.136.22.122"
SERVER_PORT="2232"
SERVER_USER="root"
REMOTE_PATH="/opt/bom_check"
LOCAL_PATH="/d/work/project/bom_check"

echo "========================================"
echo "BOM Check 增量上传工具"
echo "========================================"
echo ""
echo "本地路径: $LOCAL_PATH"
echo "服务器: $SERVER_USER@$SERVER_HOST:$REMOTE_PATH"
echo "端口: $SERVER_PORT"
echo ""

# 检查是否在 Git 仓库中
if [ ! -d "$LOCAL_PATH/.git" ]; then
    echo "⚠️  警告: 未检测到 Git 仓库"
    echo "   将进行全量上传"
    echo ""
    read -p "确认上传? (y/n) " confirm
    if [ "$confirm" != "y" ]; then
        echo "已取消"
        exit 0
    fi
    
    # 全量上传
    echo "⏳ 正在上传所有文件..."
    scp -P $SERVER_PORT -r "$LOCAL_PATH" "$SERVER_USER@$SERVER_HOST:$REMOTE_PATH/.."
else
    # 增量上传：只上传 Git 中有变化的文件
    echo "📂 检测 Git 变化..."
    
    # 获取修改、新增的文件
    CHANGED_FILES=$(cd "$LOCAL_PATH" && git diff --name-only && git ls-files -o --exclude-standard)
    
    if [ -z "$CHANGED_FILES" ]; then
        echo "✅ 没有需要上传的文件变化"
        exit 0
    fi
    
    echo "📝 需要上传的文件:"
    echo "$CHANGED_FILES" | sed 's/^/   - /'
    echo ""
    
    read -p "确认上传这些文件? (y/n) " confirm
    if [ "$confirm" != "y" ]; then
        echo "已取消"
        exit 0
    fi
    
    echo "⏳ 正在上传变化的文件..."
    
    # 创建临时目录结构并上传
    cd "$LOCAL_PATH"
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            remote_dir=$(dirname "$file")
            scp -P $SERVER_PORT "$file" "$SERVER_USER@$SERVER_HOST:$REMOTE_PATH/$remote_dir/" || true
        fi
    done <<< "$CHANGED_FILES"
fi

echo ""
echo "✅ 上传完成!"
echo ""
echo "📋 后续操作建议："
echo "  1. 连接到服务器进行验证"
echo "     ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST"
echo ""
echo "  2. 检查文件完整性"
echo "     cd $REMOTE_PATH && ls -la"
echo ""
echo "  3. 重启应用服务"
echo "     systemctl restart bom-api"
echo "     systemctl restart bom-sync"
echo ""
