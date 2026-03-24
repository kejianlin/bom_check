# BOM检查系统 - 改进版部署指南

本文档基于实际部署经验编写，解决了所有已知问题。

## 快速部署（5步完成）

### 1. 环境检查

```bash
# 上传项目到服务器
scp -P 2232 -r bom_check root@your-server:/tmp/

# 连接服务器
ssh -p 2232 root@your-server

# 运行环境检查
cd /tmp/bom_check
python3 check_environment.py
```

### 2. 修复行尾符（Windows部署必需）

```bash
cd /tmp/bom_check
bash deploy/scripts/fix_line_endings.sh
```

### 3. 一键部署

```bash
# 运行部署脚本
bash deploy/scripts/deploy.sh

# 配置数据库连接
vim /opt/bom_check/.env
```

### 4. 创建MySQL表

```bash
cd /opt/bom_check

# 方式1：自动从Oracle生成（推荐）
sudo -u bomuser venv/bin/python scripts/create_mysql_tables.py

# 方式2：手动导入已有数据
mysql -uroot -p plm_sync_db < your_backup.sql
```

### 5. 启动服务

```bash
# 启动API
systemctl start bom-api
systemctl status bom-api

# 启动定时同步
systemctl start bom-sync.timer

# 测试
curl http://localhost:5000/api/health
```

## 常见问题及解决方案

### Python版本问题

**问题：** Python 3.6不支持新版依赖

**解决：**
```bash
# 方案1：升级Python（推荐）
yum install -y python38
python3.8 -m venv /opt/bom_check/venv

# 方案2：使用兼容版本（已在requirements.txt中配置）
pip install -r requirements.txt
```

### 行尾符问题

**问题：** `bash: $'\r': command not found`

**解决：**
```bash
bash deploy/scripts/fix_line_endings.sh
```

### MySQL行大小超限

**问题：** `Row size too large`

**解决：** 使用自动建表脚本，会自动优化字段类型
```bash
python scripts/create_mysql_tables.py
```

### Oracle连接失败

**问题：** Oracle 11g需要Thick模式

**解决：**
```bash
# 安装Oracle Instant Client
cd /opt
wget https://download.oracle.com/otn_software/linux/instantclient/1912000/instantclient-basic-linux.x64-19.12.0.0.0dbru.zip
unzip instantclient-basic-linux.x64-19.12.0.0.0dbru.zip
mv instantclient_19_12 /opt/oracle/

# 配置
yum install -y libaio
echo "/opt/oracle/instantclient_19_12" > /etc/ld.so.conf.d/oracle.conf
ldconfig
```

## 优化后的特性

### ✅ 自动环境检查
- Python版本检查
- 依赖包检查
- 配置文件检查
- 目录结构检查

### ✅ 兼容性改进
- 支持Python 3.6+
- 自动处理行尾符
- 数据库类型自动转换

### ✅ 自动化工具
- 自动建表脚本
- 环境检查脚本
- 行尾符修复脚本

### ✅ 错误处理
- 详细的错误日志
- 友好的错误提示
- 自动重试机制

## 部署检查清单

- [ ] Python 3.6+ 已安装
- [ ] MySQL 8.0+ 已安装
- [ ] Oracle Instant Client 已安装（如需连接Oracle 11g）
- [ ] 环境检查通过
- [ ] 行尾符已修复
- [ ] 配置文件已编辑
- [ ] MySQL表已创建
- [ ] 服务已启动
- [ ] API测试通过

## 维护命令

```bash
# 查看服务状态
systemctl status bom-api bom-sync.timer

# 查看日志
journalctl -u bom-api -f
tail -f /opt/bom_check/logs/api_service.log

# 手动同步
systemctl start bom-sync

# 健康检查
python check_environment.py
bash deploy/scripts/health_check.sh
```

## 总结

通过这些优化，部署过程更加：
- 🚀 **快速**：5步完成部署
- 🛡️ **可靠**：自动检查和修复常见问题
- 📝 **清晰**：详细的错误提示和文档
- 🔧 **灵活**：支持多种Python版本和数据库