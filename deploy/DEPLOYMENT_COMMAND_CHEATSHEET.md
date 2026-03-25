# 快速参考 - 部署命令速查表

## 🚀 一键式命令

### Windows PowerShell
```powershell
# 完整上传
cd D:\work\project\bom_check; .\deploy\upload_to_server.ps1
```

### Git Bash
```bash
# 仅上传修改的文件
cd /d/work/project/bom_check
chmod +x deploy/upload_changes.sh
./deploy/upload_changes.sh
```

### 命令行直接上传
```bash
# 完整项目（Windows PowerShell）
scp -P 2232 -r "D:\work\project\bom_check" root@119.136.22.122:/opt/

# 仅关键文件夹（Git Bash）
scp -P 2232 -r /d/work/project/bom_check/validator root@119.136.22.122:/opt/bom_check/
scp -P 2232 -r /d/work/project/bom_check/config root@119.136.22.122:/opt/bom_check/
scp -P 2232 -r /d/work/project/bom_check/utils root@119.136.22.122:/opt/bom_check/
```

---

## 🔐 服务器连接

```bash
# SSH 连接
ssh -p 2232 root@119.136.22.122

# 其中：
# -p 2232     使用端口 2232
# root        用户名
# 119.136.22.122  服务器 IP
```

---

## 📁 关键文件路径

### 本地（Windows）
```
D:\work\project\bom_check\
├── validator\
│   ├── enhanced_rules.py          ← VR100 规则在这里
│   ├── data_checker.py            ← 数据校验
│   └── db_validator.py            ← 数据库校验
├── config\
│   └── validation_rules_new.yaml   ← VR100 配置在这里
├── utils\
│   └── db_helper.py               ← 数据库连接
└── deploy\
    ├── upload_to_server.ps1       ← PowerShell 上传脚本
    ├── upload_changes.sh          ← Bash 增量上传脚本
    ├── upload_to_server.bat       ← 批处理上传脚本
    ├── UPLOAD_GUIDE.md            ← 详细上传指南
    ├── LOCAL_DEPLOYMENT_CHECKLIST.md  ← 检查清单
    └── DEPLOYMENT_COMMAND_CHEATSHEET.md ← 本文件
```

### 服务器（Linux）
```
/opt/bom_check/
├── validator/
├── config/
├── utils/
└── logs/
    └── bom_check.log
```

---

## ⚙️ 上传后的服务器操作

### 连接到服务器
```bash
ssh -p 2232 root@119.136.22.122
```

### 验证文件
```bash
# 进入项目目录
cd /opt/bom_check

# 检查文件是否存在
ls -la validator/enhanced_rules.py
ls -la config/validation_rules_new.yaml

# 查看文件大小和时间
ls -lh config/validation_rules_new.yaml

# 验证文件内容中包含特定字符串
grep -n "child_code_position_match\|ChildCodePositionMatchRule" validator/enhanced_rules.py
grep -n "child_to_position_map" config/validation_rules_new.yaml
```

### 安装依赖
```bash
# 进入项目目录
cd /opt/bom_check

# 安装所有依赖
pip install -r requirements.txt

# 检查特定包
pip list | grep -E "flask|sqlalchemy|openpyxl"
```

### 重启服务
```bash
# Systemd 方式（推荐）
systemctl restart bom-api
systemctl restart bom-sync
systemctl status bom-api      # 检查状态

# Docker 方式
cd /opt/bom_check/deploy
docker-compose -f docker-compose.prod.yml restart

# 查看日志
tail -f /opt/bom_check/logs/bom_check.log
```

---

## 🧪 快速测试

### 本地测试（上传前）
```bash
# Windows PowerShell
cd D:\work\project\bom_check

# 语法检查
python -m py_compile validator\enhanced_rules.py
python -m py_compile validator\data_checker.py

# 配置文件验证
python -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml')); print('OK')"
```

### 服务器测试（上传后）
```bash
# SSH 连接后
cd /opt/bom_check

# 语法检查
python3 -m py_compile validator/*.py

# 配置文件验证
python3 -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml')); print('配置文件有效')"

# 数据库连接测试
python3 << 'EOF'
from utils.db_helper import DatabaseHelper
db = DatabaseHelper()
print("✓ 数据库连接成功")
EOF

# VR100 规则测试
python3 << 'EOF'
from validator.enhanced_rules import ChildCodePositionMatchRule
rule = ChildCodePositionMatchRule()
result = rule.validate("RED-00001", ["R001"])
print(f"✓ VR100 规则加载成功: {result}")
EOF
```

---

## 📊 日志查看

### 查看日志
```bash
# 最后 20 行
tail -20 /opt/bom_check/logs/bom_check.log

# 实时日志（按 Ctrl+C 退出）
tail -f /opt/bom_check/logs/bom_check.log

# 搜索错误
grep -i "error\|exception" /opt/bom_check/logs/bom_check.log

# 显示行号
tail -20 -n /opt/bom_check/logs/bom_check.log | cat -n
```

### 查看系统信息
```bash
# CPU 和内存使用
top -bn1 | head -20

# 磁盘使用
df -h

# 内存详情
free -h

# 进程查看
ps aux | grep python
```

---

## 🔧 常见操作

### 编辑远程文件
```bash
# SSH 后使用 nano 编辑
nano /opt/bom_check/config/validation_rules_new.yaml

# 保存：Ctrl+O，确认，Ctrl+X 退出
# 或使用 vi
vi /opt/bom_check/config/validation_rules_new.yaml
```

### 下载服务器文件
```bash
# Git Bash 或 PowerShell
scp -P 2232 root@119.136.22.122:/opt/bom_check/logs/bom_check.log ./

# ETL 本地日志位置
# Windows: D:\work\project\bom_check\local_log.txt
```

### 清理临时文件
```bash
# 进入服务器
cd /opt/bom_check

# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 清理旧日志（保留最近 7 天）
find /opt/bom_check/logs -name "*.log" -mtime +7 -delete
```

---

## 🚨 故障排查速查

| 问题 | 命令 |
|------|------|
| scp 找不到 | `where scp` (Windows) 或 `which scp` (Linux) |
| 连接超时 | `ping 119.136.22.122` 和 `ssh -p 2232 -v root@119.136.22.122` |
| 密码错误 | 确认 root 密码是否正确 |
| 服务不启动 | `systemctl status bom-api` 和查看日志 |
| 数据库连接失败 | `python3 -c "import utils.db_helper"` 检查导入 |
| 配置文件错误 | `python3 -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml'))"` |

---

## 📝 上传前检查清单

```bash
# 快速版本（5 分钟）
python -m py_compile validator\*.py
python -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml'))"
echo "✓ 所有检查通过"

# 详细版本
python -m py_compile validator\*.py
python -m py_compile utils\*.py
python -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml'))"
python bom_validator.py --syntax-check
echo "✓ 详细检查完毕"
```

---

## 💾 备份相关

### 本地备份
```bash
# 打包整个项目
tar.exe -czf bom_check_backup_$(date +%Y%m%d).tar.gz D:\work\project\bom_check

# 或使用 7-Zip（Windows）
7z a bom_check_backup_20240324.7z D:\work\project\bom_check
```

### 服务器备份
```bash
# SSH 连接后
cd /opt && tar -czf bom_check_backup_$(date +%Y%m%d).tar.gz bom_check/
ls -lh bom_check_backup_*.tar.gz

# 下载备份到本地
scp -P 2232 root@119.136.22.122:/opt/bom_check_backup_*.tar.gz ./
```

---

## 📞 需要帮助

- 完整文档：`deploy/UPLOAD_GUIDE.md`
- 详细检查清单：`deploy/LOCAL_DEPLOYMENT_CHECKLIST.md`
- 查看日志：`tail -f /opt/bom_check/logs/bom_check.log`
- 服务状态：`systemctl status bom-api bom-sync`

---

**提示**：将此文件保存为书签或打印出来，以便快速参考。

**最后更新**: 2026-03-24  
**适用版本**: BOM Check v2.0+
