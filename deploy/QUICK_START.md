# BOM检查系统 - 快速部署指南

## 5分钟快速部署

### 前提条件

- ✅ Linux服务器（Ubuntu/CentOS/RHEL）
- ✅ root或sudo权限
- ✅ 能访问PLM生产数据库
- ✅ MySQL 8.0已安装（或使用Docker）

---

## 部署步骤

### 1️⃣ 上传项目文件

```bash
# 方式1: 使用scp上传
scp -r bom_check root@your-server:/tmp/

# 方式2: 使用git克隆
ssh root@your-server
cd /tmp
git clone <your-repo-url> bom_check
```

### 2️⃣ 运行自动部署脚本

```bash
cd /tmp/bom_check
sudo bash deploy/scripts/deploy.sh
```

脚本会自动完成所有安装配置，按提示操作即可。

### 3️⃣ 配置数据库连接

```bash
sudo vim /opt/bom_check/.env
```

修改以下内容：

```bash
# PLM生产数据库（只读）- 必须修改
PLM_DB_TYPE=oracle
PLM_DB_HOST=192.168.1.111
PLM_DB_PORT=1521
PLM_DB_NAME=sycpcdb
PLM_DB_USER=cpcbase
PLM_DB_PASSWORD=your_real_password

# PLM同步数据库 - 必须修改
SYNC_DB_HOST=localhost
SYNC_DB_NAME=plm_sync_db
SYNC_DB_USER=sync_user
SYNC_DB_PASSWORD=your_sync_password
```

### 4️⃣ 初始化同步数据库

```bash
cd /opt/bom_check
sudo -u bomuser venv/bin/python sync/plm_sync.py --init
```

### 5️⃣ 启动服务

```bash
# 启动API服务
sudo systemctl start bom-api

# 启动同步定时器（每天凌晨2点自动同步）
sudo systemctl start bom-sync.timer

# 查看服务状态
sudo systemctl status bom-api
sudo systemctl status bom-sync.timer
```

### 6️⃣ 验证部署

```bash
# 测试API
curl http://localhost:5000/api/health

# 应该返回：
# {"status": "healthy", "timestamp": "2026-03-06T10:00:00"}

# 手动执行一次同步测试
sudo systemctl start bom-sync

# 查看同步日志
sudo journalctl -u bom-sync -f
```

---

## 完成！🎉

您的BOM检查系统已经部署完成！

### 访问API

- **本地访问**: `http://localhost:5000/api/`
- **远程访问**: `http://your-server-ip:5000/api/`

### 主要功能

1. **BOM校验**: 上传Excel文件进行BOM校验
2. **自动同步**: 每天凌晨2点自动从PLM同步数据
3. **报告生成**: 自动生成Excel和HTML格式的校验报告

### 常用命令

```bash
# 查看API日志
sudo journalctl -u bom-api -f

# 查看同步日志
sudo journalctl -u bom-sync -f

# 重启API服务
sudo systemctl restart bom-api

# 手动执行同步
sudo systemctl start bom-sync

# 健康检查
sudo bash /opt/bom_check/deploy/scripts/health_check.sh
```

---

## 使用Docker部署（可选）

如果您更喜欢使用Docker：

```bash
# 1. 进入Docker配置目录
cd bom_check/deploy/docker

# 2. 配置环境变量
cp .env.example .env
vim .env  # 修改数据库配置

# 3. 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 4. 初始化数据库
docker exec -it bom_validator_api python sync/plm_sync.py --init

# 5. 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 6. 测试API
curl http://localhost:5000/api/health
```

---

## 定时同步配置

系统默认每天凌晨2点自动同步PLM数据。

### 修改同步时间

```bash
# 编辑定时器配置
sudo vim /etc/systemd/system/bom-sync.timer

# 修改执行时间（例如改为每天凌晨3点）
OnCalendar=*-*-* 03:00:00

# 重新加载配置
sudo systemctl daemon-reload
sudo systemctl restart bom-sync.timer
```

### 常用时间配置

```ini
# 每天凌晨2点
OnCalendar=*-*-* 02:00:00

# 每12小时（0点和12点）
OnCalendar=*-*-* 00,12:00:00

# 每周一凌晨3点
OnCalendar=Mon *-*-* 03:00:00

# 每月1号凌晨4点
OnCalendar=*-*-01 04:00:00
```

---

## 配置Nginx反向代理（可选）

如果需要通过域名访问或配置HTTPS：

```bash
# 1. 安装Nginx
sudo apt-get install nginx  # Ubuntu/Debian
sudo yum install nginx      # CentOS/RHEL

# 2. 复制配置文件
sudo cp deploy/nginx/bom-api.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/bom-api.conf /etc/nginx/sites-enabled/

# 3. 修改域名
sudo vim /etc/nginx/sites-available/bom-api.conf
# 修改 server_name 为您的域名

# 4. 测试配置
sudo nginx -t

# 5. 重启Nginx
sudo systemctl restart nginx

# 6. 访问API
curl http://your-domain.com/api/health
```

---

## 故障排查

### API无法访问

```bash
# 检查服务状态
sudo systemctl status bom-api

# 查看错误日志
sudo journalctl -u bom-api -n 50

# 检查端口占用
sudo netstat -tlnp | grep 5000

# 检查防火墙
sudo firewall-cmd --list-ports  # CentOS/RHEL
sudo ufw status                 # Ubuntu
```

### 同步失败

```bash
# 查看同步日志
sudo journalctl -u bom-sync -n 100

# 手动执行同步查看详细错误
cd /opt/bom_check
sudo -u bomuser venv/bin/python sync/plm_sync.py --mode incremental

# 测试数据库连接
mysql -h localhost -u sync_user -p plm_sync_db
```

### 数据库连接失败

```bash
# 测试PLM生产库连接
telnet 192.168.1.111 1521

# 测试MySQL连接
mysql -h localhost -u sync_user -p

# 查看详细错误
sudo tail -f /opt/bom_check/logs/bom_check.log
```

---

## 下一步

1. **配置通知**: 编辑 `config/sync_config.yaml` 配置邮件通知
2. **查看文档**: 阅读 `DEPLOYMENT.md` 了解详细配置
3. **性能优化**: 根据数据量调整 `sync_config.yaml` 中的批量大小和并发数
4. **安全加固**: 配置防火墙、HTTPS、数据库访问控制

---

## 获取帮助

- 📖 详细文档: `DEPLOYMENT.md`
- 🔧 配置说明: `config/sync_config.yaml`
- 📝 查看日志: `/opt/bom_check/logs/`
- 🏥 健康检查: `bash deploy/scripts/health_check.sh`
