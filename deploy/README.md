# BOM检查系统 - 部署文件说明

本目录包含BOM检查系统在Linux服务器上部署所需的所有配置文件和脚本。

## 📁 目录结构

```
deploy/
├── README.md                    # 本文件
├── QUICK_START.md              # 快速开始指南（5分钟部署）
├── CHECKLIST.md                # 部署检查清单
├── systemd/                    # systemd服务配置
│   ├── bom-api.service        # API服务配置
│   ├── bom-sync.service       # 同步服务配置
│   └── bom-sync.timer         # 同步定时器配置
├── cron/                       # cron定时任务配置
│   └── bom-sync-cron          # cron任务配置文件
├── scripts/                    # 部署和运维脚本
│   ├── deploy.sh              # 自动化部署脚本
│   ├── backup_database.sh     # 数据库备份脚本
│   ├── restore_database.sh    # 数据库恢复脚本
│   └── health_check.sh        # 健康检查脚本
├── nginx/                      # Nginx配置
│   └── bom-api.conf           # Nginx反向代理配置
└── docker/                     # Docker部署配置
    ├── docker-compose.prod.yml # 生产环境Docker Compose配置
    └── .env.example           # Docker环境变量示例
```

## 🚀 快速开始

### 方式1: 自动化脚本部署（推荐）

```bash
# 1. 上传项目到服务器
scp -r bom_check root@your-server:/tmp/

# 2. 运行部署脚本
cd /tmp/bom_check
sudo bash deploy/scripts/deploy.sh

# 3. 配置数据库连接
sudo vim /opt/bom_check/.env

# 4. 初始化数据库
cd /opt/bom_check
sudo -u bomuser venv/bin/python sync/plm_sync.py --init

# 5. 启动服务
sudo systemctl start bom-api
sudo systemctl start bom-sync.timer
```

### 方式2: Docker部署

```bash
# 1. 配置环境变量
cd deploy/docker
cp .env.example .env
vim .env

# 2. 启动服务
docker compose -f docker-compose.prod.yml up -d

# 3. 初始化数据库
docker exec -it bom_validator_api python sync/plm_sync.py --init
```

详细说明请参考: [QUICK_START.md](QUICK_START.md)

## 📋 文件说明

### systemd服务配置

#### bom-api.service
API服务的systemd配置文件，用于管理BOM校验API服务。

**特点:**
- 自动重启
- 日志记录
- 依赖MySQL服务
- 开机自启

**使用:**
```bash
sudo systemctl start bom-api      # 启动
sudo systemctl stop bom-api       # 停止
sudo systemctl restart bom-api    # 重启
sudo systemctl status bom-api     # 状态
```

#### bom-sync.service
数据同步服务的systemd配置文件，用于执行PLM数据同步任务。

**特点:**
- 一次性任务（oneshot）
- 超时保护（2小时）
- 日志记录
- 由定时器触发

**使用:**
```bash
sudo systemctl start bom-sync     # 手动执行同步
sudo journalctl -u bom-sync -f    # 查看日志
```

#### bom-sync.timer
数据同步定时器配置文件，用于定时触发同步任务。

**特点:**
- 每天凌晨2点执行
- 错过时间自动补执行
- 系统启动5分钟后首次执行

**使用:**
```bash
sudo systemctl start bom-sync.timer    # 启动定时器
sudo systemctl status bom-sync.timer   # 查看状态
sudo systemctl list-timers             # 查看下次执行时间
```

### cron定时任务

#### bom-sync-cron
cron格式的定时任务配置，作为systemd timer的备选方案。

**任务:**
- 每天凌晨2点: 增量同步
- 每周日凌晨3点: 全量同步
- 每天凌晨1点: 清理旧日志
- 每月1号凌晨4点: 数据库备份

**安装:**
```bash
sudo cp deploy/cron/bom-sync-cron /etc/cron.d/bom-sync
sudo chmod 644 /etc/cron.d/bom-sync
```

### 部署和运维脚本

#### deploy.sh
自动化部署脚本，一键完成所有部署步骤。

**功能:**
- 检测操作系统
- 安装系统依赖
- 创建应用用户
- 配置Python环境
- 安装systemd服务
- 配置防火墙

**使用:**
```bash
sudo bash deploy/scripts/deploy.sh
```

#### backup_database.sh
数据库备份脚本，支持MySQL和PostgreSQL。

**功能:**
- 自动备份同步数据库
- 压缩备份文件
- 自动清理30天前的旧备份

**使用:**
```bash
sudo bash deploy/scripts/backup_database.sh
```

#### restore_database.sh
数据库恢复脚本，从备份文件恢复数据库。

**使用:**
```bash
sudo bash deploy/scripts/restore_database.sh /path/to/backup.sql.gz
```

#### health_check.sh
系统健康检查脚本，检查各组件运行状态。

**检查项:**
- API服务状态
- 同步定时器状态
- 数据库连接
- 磁盘空间
- 日志大小

**使用:**
```bash
sudo bash deploy/scripts/health_check.sh
```

### Nginx配置

#### bom-api.conf
Nginx反向代理配置，用于生产环境部署。

**功能:**
- 反向代理到API服务
- 静态文件服务（报告下载）
- 上传大小限制（50MB）
- 健康检查端点
- HTTPS支持（可选）

**安装:**
```bash
sudo cp deploy/nginx/bom-api.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/bom-api.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Docker配置

#### docker-compose.prod.yml
生产环境的Docker Compose配置。

**服务:**
- MySQL数据库
- BOM API服务
- 数据同步调度器
- Nginx反向代理

**使用:**
```bash
cd deploy/docker
docker compose -f docker-compose.prod.yml up -d
```

## 🔧 配置修改

### 修改同步时间

**systemd方式:**
```bash
sudo vim /etc/systemd/system/bom-sync.timer
# 修改 OnCalendar=*-*-* 02:00:00
sudo systemctl daemon-reload
sudo systemctl restart bom-sync.timer
```

**cron方式:**
```bash
sudo vim /etc/cron.d/bom-sync
# 修改 0 2 * * * 为其他时间
```

### 修改API端口

```bash
# 修改环境变量
sudo vim /opt/bom_check/.env
# 添加: API_PORT=8000

# 修改systemd服务
sudo vim /etc/systemd/system/bom-api.service
# 确保环境变量正确

# 重启服务
sudo systemctl daemon-reload
sudo systemctl restart bom-api
```

### 修改日志级别

```bash
sudo vim /opt/bom_check/.env
# 修改: LOG_LEVEL=DEBUG  # INFO/WARNING/ERROR
sudo systemctl restart bom-api
```

## 📊 监控和日志

### 查看服务状态

```bash
# API服务
sudo systemctl status bom-api

# 同步定时器
sudo systemctl status bom-sync.timer

# 查看下次同步时间
sudo systemctl list-timers bom-sync.timer
```

### 查看日志

```bash
# API日志
sudo journalctl -u bom-api -f

# 同步日志
sudo journalctl -u bom-sync -f

# 应用日志
sudo tail -f /opt/bom_check/logs/bom_check.log

# 查看最近100行
sudo journalctl -u bom-api -n 100
```

### 健康检查

```bash
# 运行健康检查脚本
sudo bash /opt/bom_check/deploy/scripts/health_check.sh

# 测试API
curl http://localhost:5000/api/health

# 查看同步统计
cd /opt/bom_check
sudo -u bomuser venv/bin/python sync/plm_sync.py --stats --days 7
```

## 🔒 安全建议

1. **数据库安全**
   - PLM生产库使用只读账号
   - 使用强密码（至少16位，包含大小写字母、数字、特殊字符）
   - 限制数据库访问IP白名单

2. **文件权限**
   - `.env` 文件权限设置为 600
   - 应用文件属于 `bomuser:bomuser`
   - 日志目录只允许应用用户写入

3. **网络安全**
   - 使用防火墙限制访问端口
   - 考虑使用VPN访问PLM数据库
   - 生产环境启用HTTPS

4. **定期备份**
   - 配置自动备份任务
   - 定期测试恢复流程
   - 备份文件异地存储

## 🆘 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u bom-api -n 50

# 检查端口占用
sudo netstat -tlnp | grep 5000

# 手动启动测试
cd /opt/bom_check
sudo -u bomuser venv/bin/python api_server.py
```

### 同步失败

```bash
# 查看同步日志
sudo journalctl -u bom-sync -n 100

# 手动执行同步
cd /opt/bom_check
sudo -u bomuser venv/bin/python sync/plm_sync.py --mode incremental

# 测试数据库连接
mysql -h localhost -u sync_user -p plm_sync_db
```

### 数据库连接失败

```bash
# 测试网络连接
telnet PLM_DB_HOST PLM_DB_PORT

# 查看错误日志
sudo tail -f /opt/bom_check/logs/bom_check.log | grep -i error
```

## 📚 相关文档

- [DEPLOYMENT.md](../DEPLOYMENT.md) - 完整部署文档
- [QUICK_START.md](QUICK_START.md) - 快速开始指南
- [CHECKLIST.md](CHECKLIST.md) - 部署检查清单
- [README.md](../README.md) - 项目主文档

## 🤝 获取帮助

如遇到问题，请提供以下信息：

1. 操作系统版本: `cat /etc/os-release`
2. 错误日志: `journalctl -u bom-api -n 100`
3. 服务状态: `systemctl status bom-api`
4. 配置文件（隐藏敏感信息）

## 📝 更新日志

- 2026-03-06: 创建部署文件和文档
- 支持Ubuntu/CentOS/RHEL系统
- 提供systemd和Docker两种部署方式
- 包含完整的运维脚本
