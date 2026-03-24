#!/bin/bash
###############################################################################
# 修复Windows行尾符问题
# 用途：将CRLF转换为LF
###############################################################################

echo "修复Shell脚本行尾符..."

# 查找所有.sh文件并转换
find . -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;

# 设置执行权限
find . -name "*.sh" -type f -exec chmod +x {} \;

echo "修复Python脚本行尾符..."
find . -name "*.py" -type f -exec sed -i 's/\r$//' {} \;

echo "完成！"
