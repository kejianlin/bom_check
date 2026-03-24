#!/bin/bash
###############################################################################
# BOM检查系统 - Linux部署脚本
# 用途：自动化部署BOM校验系统到Linux服务器
# 使用：sudo bash deploy.sh
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
APP_NAME="bom_check"
APP_USER="bomuser"
APP_GROUP="bomuser"
INSTALL_DIR="/opt/bom_check"
PYTHON_VERSION="3.10"
VENV_DIR="${INSTALL_DIR}/venv"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以root权限运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        log_info "请使用: sudo bash deploy.sh"
        exit 1
    fi
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

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        apt-get update
        apt-get install -y \
            python3.10 \
            python3.10-venv \
            python3-pip \
            gcc \
            g++ \
            make \
            libmysqlclient-dev \
            default-libmysqlclient-dev \
            postgresql-client \
            libpq-dev \
            git \
            curl \
            vim \
            supervisor
            
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "rocky" ]]; then
        yum install -y epel-release
        yum install -y \
            python3.10 \
            python3-pip \
            gcc \
            gcc-c++ \
            make \
            mysql-devel \
            postgresql-devel \
            git \
            curl \
            vim \
            supervisor
    else
        log_error "不支持的操作系统: $OS"
        exit 1
    fi
    
    log_info "系统依赖安装完成"
}

# 创建应用用户
create_app_user() {
    log_info "创建应用用户: $APP_USER"
    
    if id "$APP_USER" &>/dev/null; then
        log_warn "用户 $APP_USER 已存在，跳过创建"
    else
        useradd -r -m -s /bin/bash -d /home/$APP_USER $APP_USER
        log_info "用户 $APP_USER 创建成功"
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    mkdir -p $INSTALL_DIR
    mkdir -p $INSTALL_DIR/logs
    mkdir -p $INSTALL_DIR/reports
    mkdir -p $INSTALL_DIR/temp/uploads
    mkdir -p $INSTALL_DIR/config
    mkdir -p $INSTALL_DIR/backup
    
    log_info "目录创建完成"
}

# 复制应用文件
copy_application() {
    log_info "复制应用文件到 $INSTALL_DIR ..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    
    # 复制主要文件和目录
    cp -r $SCRIPT_DIR/config $INSTALL_DIR/
    cp -r $SCRIPT_DIR/models $INSTALL_DIR/
    cp -r $SCRIPT_DIR/report $INSTALL_DIR/
    cp -r $SCRIPT_DIR/scripts $INSTALL_DIR/
    cp -r $SCRIPT_DIR/sync $INSTALL_DIR/
    cp -r $SCRIPT_DIR/utils $INSTALL_DIR/
    cp -r $SCRIPT_DIR/validator $INSTALL_DIR/
    cp -r $SCRIPT_DIR/templates $INSTALL_DIR/
    
    cp $SCRIPT_DIR/api_server.py $INSTALL_DIR/
    cp $SCRIPT_DIR/bom_validator.py $INSTALL_DIR/
    cp $SCRIPT_DIR/requirements.txt $INSTALL_DIR/
    
    # 复制环境配置示例
    if [ ! -f $INSTALL_DIR/.env ]; then
        cp $SCRIPT_DIR/.env.example $INSTALL_DIR/.env
        log_warn "请编辑 $INSTALL_DIR/.env 配置数据库连接信息"
    fi
    
    log_info "应用文件复制完成"
}

# 创建Python虚拟环境
setup_virtualenv() {
    log_info "创建Python虚拟环境..."
    
    if [ -d "$VENV_DIR" ]; then
        log_warn "虚拟环境已存在，将重新创建"
        rm -rf $VENV_DIR
    fi
    
    python3.10 -m venv $VENV_DIR
    
    # 激活虚拟环境并安装依赖
    source $VENV_DIR/bin/activate
    pip install --upgrade pip
    pip install -r $INSTALL_DIR/requirements.txt
    pip install gunicorn waitress
    deactivate
    
    log_info "Python虚拟环境创建完成"
}

# 设置文件权限
set_permissions() {
    log_info "设置文件权限..."
    
    chown -R $APP_USER:$APP_GROUP $INSTALL_DIR
    chmod -R 755 $INSTALL_DIR
    chmod -R 777 $INSTALL_DIR/logs
    chmod -R 777 $INSTALL_DIR/reports
    chmod -R 777 $INSTALL_DIR/temp
    chmod 600 $INSTALL_DIR/.env
    
    # 设置脚本可执行权限
    chmod +x $INSTALL_DIR/api_server.py
    chmod +x $INSTALL_DIR/bom_validator.py
    chmod +x $INSTALL_DIR/sync/plm_sync.py
    
    log_info "文件权限设置完成"
}

# 安装systemd服务
install_systemd_services() {
    log_info "安装systemd服务..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    
    # 复制服务文件
    cp $SCRIPT_DIR/deploy/systemd/bom-api.service /etc/systemd/system/
    cp $SCRIPT_DIR/deploy/systemd/bom-sync.service /etc/systemd/system/
    cp $SCRIPT_DIR/deploy/systemd/bom-sync.timer /etc/systemd/system/
    
    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable bom-api.service
    systemctl enable bom-sync.timer
    
    log_info "systemd服务安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    if command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL使用firewalld
        firewall-cmd --permanent --add-port=5000/tcp
        firewall-cmd --reload
        log_info "firewalld配置完成"
    elif command -v ufw &> /dev/null; then
        # Ubuntu使用ufw
        ufw allow 5000/tcp
        log_info "ufw配置完成"
    else
        log_warn "未检测到防火墙，跳过配置"
    fi
}

# 初始化数据库
initialize_database() {
    log_info "初始化同步数据库..."
    
    cd $INSTALL_DIR
    sudo -u $APP_USER $VENV_DIR/bin/python sync/plm_sync.py --init
    
    log_info "数据库初始化完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动API服务
    systemctl start bom-api.service
    systemctl status bom-api.service --no-pager
    
    # 启动定时器
    systemctl start bom-sync.timer
    systemctl status bom-sync.timer --no-pager
    
    log_info "服务启动完成"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "=========================================="
    echo "  BOM检查系统部署完成！"
    echo "=========================================="
    echo ""
    echo "安装目录: $INSTALL_DIR"
    echo "应用用户: $APP_USER"
    echo "API地址: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "服务管理命令:"
    echo "  启动API服务:  systemctl start bom-api"
    echo "  停止API服务:  systemctl stop bom-api"
    echo "  重启API服务:  systemctl restart bom-api"
    echo "  查看API状态:  systemctl status bom-api"
    echo ""
    echo "  查看同步定时器: systemctl status bom-sync.timer"
    echo "  手动执行同步:   systemctl start bom-sync"
    echo "  查看同步日志:   journalctl -u bom-sync -f"
    echo ""
    echo "日志文件:"
    echo "  API日志:  $INSTALL_DIR/logs/api_service.log"
    echo "  同步日志: $INSTALL_DIR/logs/sync_service.log"
    echo "  应用日志: $INSTALL_DIR/logs/bom_check.log"
    echo ""
    echo "配置文件:"
    echo "  环境配置: $INSTALL_DIR/.env"
    echo "  数据库配置: $INSTALL_DIR/config/database.yaml"
    echo "  同步配置: $INSTALL_DIR/config/sync_config.yaml"
    echo ""
    echo "下一步操作:"
    echo "  1. 编辑配置文件: vim $INSTALL_DIR/.env"
    echo "  2. 重启服务: systemctl restart bom-api"
    echo "  3. 测试API: curl http://localhost:5000/api/health"
    echo ""
}

# 主函数
main() {
    log_info "开始部署BOM检查系统..."
    
    check_root
    detect_os
    install_dependencies
    create_app_user
    create_directories
    copy_application
    setup_virtualenv
    set_permissions
    install_systemd_services
    configure_firewall
    
    # 询问是否初始化数据库
    read -p "是否初始化同步数据库? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        initialize_database
    fi
    
    # 询问是否启动服务
    read -p "是否立即启动服务? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_services
    fi
    
    show_deployment_info
    
    log_info "部署完成！"
}

# 执行主函数
main
