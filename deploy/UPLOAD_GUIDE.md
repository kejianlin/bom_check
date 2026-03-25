# BOM Check 项目上传指南

## 📋 概述

本指南说明如何将本地修改的 BOM Check 项目文件上传到服务器。

**服务器信息**：
- 服务器地址: 119.136.22.122
- SSH 端口: 2232
- 服务器用户: root
- 远程路径: /opt/bom_check

---

## 🔧 前置条件

### Windows 10+ 用户
1. **安装 OpenSSH 客户端**：
   - 打开 Settings (设置)
   - Apps → Apps & Features → Optional Features
   - 搜索 "OpenSSH Client"
   - 点击 "Add" 安装

2. **或者使用 Git Bash**：
   - 从 https://git-scm.com/download/win 下载并安装 Git
   - Git Bash 内置了 scp 和 ssh

### macOS/Linux 用户
- 系统已内置 ssh 和 scp，无需额外安装

---

## 📤 上传方式

### 方式 1: PowerShell 脚本（推荐 - 交互式）

**步骤**：
1. 打开 PowerShell
2. 进入项目目录：
   ```powershell
   cd D:\work\project\bom_check
   ```
3. 运行上传脚本：
   ```powershell
   .\deploy\upload_to_server.ps1
   ```
4. 按照提示操作

**功能**：
- ✅ 自动检测项目文件
- ✅ 显示文件数量
- ✅ 需要确认后上传
- ✅ 上传完成后给出后续建议

---

### 方式 2: Windows 批处理脚本

**步骤**：
1. 双击 `deploy/upload_to_server.bat`
2. 按照提示操作

**功能**：
- ✅ 无需 PowerShell 基础
- ✅ 简单易用
- ✅ 适合快速上传

---

### 方式 3: Git Bash 增量上传

**步骤**：
1. 打开 Git Bash
2. 导航到项目目录：
   ```bash
   cd /d/work/project/bom_check
   ```
3. 运行增量上传脚本：
   ```bash
   chmod +x deploy/upload_changes.sh
   ./deploy/upload_changes.sh
   ```

**功能**：
- ✅ 只上传修改过的文件（需要 Git）
- ✅ 节省带宽和时间
- ✅ 更新更快

---

### 方式 4: 命令行直接上传

#### 4.1 上传整个项目

```bash
# Windows PowerShell
scp -P 2232 -r "D:\work\project\bom_check" root@119.136.22.122:/opt/

# Git Bash / macOS / Linux
scp -P 2232 -r /d/work/project/bom_check root@119.136.22.122:/opt/
```

#### 4.2 上传单个文件

```bash
scp -P 2232 "D:\work\project\bom_check\config\validation_rules_new.yaml" root@119.136.22.122:/opt/bom_check/config/
```

#### 4.3 上传多个文件夹

```bash
scp -P 2232 -r "D:\work\project\bom_check\validator" root@119.136.22.122:/opt/bom_check/
scp -P 2232 -r "D:\work\project\bom_check\config" root@119.136.22.122:/opt/bom_check/
scp -P 2232 -r "D:\work\project\bom_check\report" root@119.136.22.122:/opt/bom_check/
```

---

## 🔐 认证方式

### 方式 A: SSH 密钥认证（推荐）

**优点**：
- 🔒 更安全
- ⚡ 无需输入密码
- 🤖 支持自动化

**配置步骤**：

1. 生成 SSH 密钥（如果未有）：
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
   ```

2. 上传公钥到服务器：
   ```bash
   scp -P 2232 ~/.ssh/id_rsa.pub root@119.136.22.122:/root/.ssh/authorized_keys
   ```

3. 测试连接：
   ```bash
   ssh -p 2232 root@119.136.22.122
   ```

### 方式 B: 密码认证

**步骤**：
1. 运行上传脚本或命令
2. 当提示 `root@119.136.22.122's password:` 时，输入密码
3. 密码输入时不会显示任何字符，直接输入后按 Enter

---

## ✅ 上传后的验证步骤

### 1. 连接到服务器验证文件

```bash
ssh -p 2232 root@119.136.22.122
cd /opt/bom_check
ls -la
```

### 2. 检查关键文件是否存在

```bash
ls -la config/validation_rules_new.yaml
ls -la validator/enhanced_rules.py
ls -la requirements.txt
```

### 3. 安装依赖（如有新包）

```bash
cd /opt/bom_check
pip install -r requirements.txt
```

### 4. 重启应用服务

```bash
systemctl restart bom-api
systemctl restart bom-sync

# 或者（如果使用 Docker）
docker-compose -f deploy/docker-compose.prod.yml restart
```

### 5. 检查服务状态

```bash
systemctl status bom-api
systemctl status bom-sync

# 查看日志
tail -f logs/bom_check.log
```

---

## 🐛 常见问题

### Q1: "scp: command not found"

**解决方案**：
- 使用 Git Bash 运行脚本
- 或在 Windows 上安装 OpenSSH Client
- 或使用 PowerShell 脚本

### Q2: "Permission denied (publickey,password)"

**解决方案**：
- 检查密码是否正确
- 检查 SSH 密钥权限：`chmod 600 ~/.ssh/id_rsa`
- 确认服务器端 SSH 配置正确

### Q3: "Connection timed out"

**解决方案**：
- 检查服务器地址是否正确
- 检查网络连接
- 检查防火墙和端口 2232 是否开放
- 检查服务器是否在线

### Q4: 上传速度太慢

**解决方案**：
- 使用增量上传只传送修改文件
- 检查网络连接速度
- 排除不必要的文件（node_modules，__pycache__ 等）

### Q5: 上传后服务无法启动

**解决方案**：
```bash
# 检查 Python 语法错误
python3 -m py_compile /opt/bom_check/validator/*.py

# 查看详细日志
cd /opt/bom_check && python3 api_server.py

# 检查依赖是否完整
pip list | grep -E "flask|sqlalchemy|openpyxl"
```

---

## 📊 上传文件清单

**核心文件**：
```
validator/           - 校验引擎
  - enhanced_rules.py      [修改] 添加 VR100 规则
  - data_checker.py        [修改] 修复数据库字段
  - db_validator.py        [修改] 修复字段映射

config/              - 配置文件
  - validation_rules_new.yaml  [修改] 添加 VR100 配置

utils/               - 工具库
  - db_helper.py           [修改] 修复环境变量加载

report/              - 报告生成
  - excel_markup_generator.py [修改] 错误标注功能
```

---

## 🔄 自动化上传任务

### 方案：定时自动上传

**在服务器创建 cron 任务**：

```bash
# 编辑 crontab
crontab -e

# 添加定时拉取更新的任务（每天 23:00）
0 23 * * * cd /opt/bom_check && git pull origin main && systemctl restart bom-api
```

**或使用客户端脚本定时上传**：

```powershell
# 创建 Windows 任务计划
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File D:\work\project\bom_check\deploy\upload_to_server.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "23:00"
Register-ScheduledTask -TaskName "BOM Check Upload" -Action $action -Trigger $trigger -RunLevel Highest
```

---

## 📞 需要帮助？

- 检查本文档和常见问题
- 查看服务器日志：`tail -f /opt/bom_check/logs/bom_check.log`
- 检查服务状态：`systemctl status bom-api`

---

**最后更新**: 2026-03-24
