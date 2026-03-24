#!/bin/bash
###############################################################################
# MySQL数据库安装和配置脚本
# 用途：在Linux服务器上安装和配置MySQL数据库
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log_info "检测到操作系统: $OS $OS_VERSION"
    else
        log_error "无法检测操作系统类型"
        exit 1
    fi
}

# 安装MySQL
install_mysql() {
    log_info "安装MySQL数据库..."
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        apt-get update
        apt-get install -y mysql-server mysql-client
        
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "rocky" ]]; then
        yum install -y mysql-server mysql
        
    else
        log_error "不支持的操作系统: $OS"
        exit 1
    fi
    
    log_info "MySQL安装完成"
}

# 启动MySQL服务
start_mysql() {
    log_info "启动MySQL服务..."
    
    systemctl start mysqld || systemctl start mysql
    systemctl enable mysqld || systemctl enable mysql
    
    log_info "MySQL服务已启动"
}

# 获取临时root密码（CentOS/RHEL）
get_temp_password() {
    if [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "rocky" ]]; then
        TEMP_PASSWORD=$(grep 'temporary password' /var/log/mysqld.log | awk '{print $NF}')
        if [ -n "$TEMP_PASSWORD" ]; then
            log_info "临时root密码: $TEMP_PASSWORD"
            echo $TEMP_PASSWORD
        fi
    fi
}

# 安全配置MySQL
secure_mysql() {
    log_info "配置MySQL安全设置..."
    
    read -sp "请输入MySQL root密码: " ROOT_PASSWORD
    echo
    read -sp "请再次输入密码确认: " ROOT_PASSWORD_CONFIRM
    echo
    
    if [ "$ROOT_PASSWORD" != "$ROOT_PASSWORD_CONFIRM" ]; then
        log_error "两次输入的密码不一致"
        exit 1
    fi
    
    # 修改root密码
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$ROOT_PASSWORD';"
    else
        TEMP_PASSWORD=$(get_temp_password)
        if [ -n "$TEMP_PASSWORD" ]; then
            mysql -u root -p"$TEMP_PASSWORD" --connect-expired-password -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$ROOT_PASSWORD';"
        else
            mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$ROOT_PASSWORD';"
        fi
    fi
    
    # 删除匿名用户
    mysql -u root -p"$ROOT_PASSWORD" -e "DELETE FROM mysql.user WHERE User='';"
    
    # 禁止root远程登录
    mysql -u root -p"$ROOT_PASSWORD" -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
    
    # 删除测试数据库
    mysql -u root -p"$ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS test;"
    mysql -u root -p"$ROOT_PASSWORD" -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
    
    # 刷新权限
    mysql -u root -p"$ROOT_PASSWORD" -e "FLUSH PRIVILEGES;"
    
    log_info "MySQL安全配置完成"
}

# 配置MySQL
configure_mysql() {
    log_info "配置MySQL..."
    
    # 复制配置文件
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    if [ -f "$SCRIPT_DIR/mysql/my.cnf" ]; then
        cp "$SCRIPT_DIR/mysql/my.cnf" /etc/mysql/conf.d/bom-sync.cnf
        log_info "MySQL配置文件已复制"
    fi
    
    # 重启MySQL
    systemctl restart mysqld || systemctl restart mysql
    
    log_info "MySQL配置完成"
}

# 初始化PLM同步数据库
init_plm_database() {
    log_info "初始化PLM同步数据库..."
    
    read -sp "请输入MySQL root密码: " ROOT_PASSWORD
    echo
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    if [ -f "$SCRIPT_DIR/mysql/init.sql" ]; then
        # 提示修改密码
        log_warn "请编辑 $SCRIPT_DIR/mysql/init.sql 修改默认密码"
        read -p "是否已修改密码? (y/n): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mysql -u root -p"$ROOT_PASSWORD" < "$SCRIPT_DIR/mysql/init.sql"
            log_info "数据库初始化完成"
        else
            log_warn "请先修改密码，然后手动执行:"
            log_warn "mysql -u root -p < $SCRIPT_DIR/mysql/init.sql"
        fi
    else
        log_error "找不到初始化脚本: $SCRIPT_DIR/mysql/init.sql"
    fi
}

# 测试连接
test_connection() {
    log_info "测试数据库连接..."
    
    read -p "请输入sync_user密码: " SYNC_PASSWORD
    
    if mysql -u sync_user -p"$SYNC_PASSWORD" plm_sync_db -e "SELECT 1;" > /dev/null 2>&1; then
        log_info "数据库连接测试成功"
    else
        log_error "数据库连接测试失败"
        exit 1
    fi
}

# 显示信息
show_info() {
    echo ""
    echo "=========================================="
    echo "  MySQL安装配置完成！"
    echo "=========================================="
    echo ""
    echo "数据库信息:"
    echo "  数据库名: plm_sync_db"
    echo "  用户名: sync_user"
    echo "  端口: 3306"
    echo ""
    echo "配置文件:"
    echo "  /etc/mysql/conf.d/bom-sync.cnf"
    echo ""
    echo "管理命令:"
    echo "  启动: systemctl start mysql"
    echo "  停止: systemctl stop mysql"
    echo "  重启: systemctl restart mysql"
    echo "  状态: systemctl status mysql"
    echo ""
    echo "连接数据库:"
    echo "  mysql -u sync_user -p plm_sync_db"
    echo ""
    echo "下一步:"
    echo "  1. 配置 /opt/bom_check/.env 文件"
    echo "  2. 运行同步程序初始化表结构"
    echo ""
}

# 主函数
main() {
    log_info "开始安装配置MySQL..."
    
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
    
    detect_os
    
    # 检查MySQL是否已安装
    if command -v mysql &> /dev/null; then
        log_warn "MySQL已安装，跳过安装步骤"
    else
        install_mysql
    fi
    
    start_mysql
    
    # 询问是否配置安全设置
    read -p "是否配置MySQL安全设置? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        secure_mysql
    fi
    
    configure_mysql
    
    # 询问是否初始化数据库
    read -p "是否初始化PLM同步数据库? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        init_plm_database
        test_connection
    fi
    
    show_info
    
    log_info "完成！"
}

# 执行主函数
main
