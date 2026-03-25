# 本地部署检查清单

## 🔍 上传前检查

- [ ] **确认所有修改已保存**
  - [ ] `validator/enhanced_rules.py` 已保存
  - [ ] `validator/data_checker.py` 已保存
  - [ ] `config/validation_rules_new.yaml` 已保存
  - [ ] `utils/db_helper.py` 已保存

- [ ] **运行本地测试验证**
  ```bash
  python -m pytest tests/ -v
  python bom_validator.py --test
  ```

- [ ] **检查 Python 语法**
  ```bash
  python -m py_compile validator/*.py
  python -m py_compile utils/*.py
  ```

- [ ] **验证配置文件**
  ```bash
  python -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml'))"
  ```

---

## 📤 上传操作流程

### 步骤 1: 选择上传方式

- [ ] **方式选择**（请选择一种）：
  - [ ] 方式 1: PowerShell 脚本（推荐）
    ```powershell
    cd D:\work\project\bom_check
    .\deploy\upload_to_server.ps1
    ```
  - [ ] 方式 2: 批处理脚本
    ```
    双击 deploy\upload_to_server.bat
    ```
  - [ ] 方式 3: Git Bash 增量上传
    ```bash
    ./deploy/upload_changes.sh
    ```
  - [ ] 方式 4: 命令行上传
- [ ] **记录开始时间**: _______________
- [ ] **记录文件总数**: _______________

### 步骤 2: 执行上传

- [ ] **网络连接检查**
  - [ ] 网络正常
  - [ ] 可以访问外网
  
- [ ] **认证方式**
  - [ ] SSH 密钥（无需输入密码）
  - [ ] 密码认证（输入 root 密码）

- [ ] **上传执行**
  - [ ] 脚本/命令成功执行
  - [ ] 没有出现错误信息
  - [ ] 显示成功完成

- [ ] **记录结束时间**: _______________

---

## ✅ 上传后验证

### 步骤 3: SSH 连接到服务器

```bash
ssh -p 2232 root@119.136.22.122
```

- [ ] 成功连接到服务器

### 步骤 4: 验证文件传输

- [ ] **检查基础目录**
  ```bash
  cd /opt/bom_check
  ls -la
  pwd
  ```
  - [ ] 目录存在并且权限正确

- [ ] **验证关键文件**
  ```bash
  ls -la validator/enhanced_rules.py
  ls -la config/validation_rules_new.yaml
  ls -la utils/db_helper.py
  ```
  - [ ] enhanced_rules.py 存在
  - [ ] validation_rules_new.yaml 存在
  - [ ] db_helper.py 存在

- [ ] **比较文件时间戳**
  ```bash
  stat validator/enhanced_rules.py
  stat config/validation_rules_new.yaml
  ```
  - [ ] 文件修改时间为最近的时间戳

### 步骤 5: Python 环境验证

- [ ] **检查 Python 版本**
  ```bash
  python3 --version
  ```
  - [ ] Python 3.8+ 已安装

- [ ] **检查依赖包**
  ```bash
  pip list | grep -E "flask|sqlalchemy|openpyxl|pyyaml|python-dotenv"
  ```
  - [ ] flask ✅
  - [ ] sqlalchemy ✅
  - [ ] openpyxl ✅
  - [ ] pyyaml ✅
  - [ ] python-dotenv ✅

- [ ] **安装缺失的依赖**（如需要）
  ```bash
  cd /opt/bom_check
  pip install -r requirements.txt
  ```

### 步骤 6: Python 语法检查

- [ ] **验证批量文件**
  ```bash
  python3 -m py_compile validator/*.py
  python3 -m py_compile utils/*.py
  echo "语法检查完毕"
  ```
  - [ ] 无语法错误

- [ ] **验证配置文件**
  ```bash
  cd /opt/bom_check
  python3 -c "import yaml; yaml.safe_load(open('config/validation_rules_new.yaml')); print('配置文件有效')"
  ```
  - [ ] 配置文件格式正确

### 步骤 7: 数据库连接测试

- [ ] **测试数据库连接**
  ```bash
  cd /opt/bom_check
  python3 -c "
from utils.db_helper import DatabaseHelper
db = DatabaseHelper()
print('数据库连接成功')
print('已加载材料数:', db.materials_count if hasattr(db, 'materials_count') else '检查中')
"
  ```
  - [ ] 数据库连接成功
  - [ ] 材料数据已加载

---

## 🚀 服务重启

### 步骤 8: 重启应用服务

- [ ] **方式选择**（根据部署方式选择）：

  **方式 A: Systemd 服务**
  ```bash
  systemctl restart bom-api
  systemctl restart bom-sync
  sleep 3
  systemctl status bom-api
  systemctl status bom-sync
  ```
  - [ ] bom-api 服务已重启并运行中
  - [ ] bom-sync 服务已重启并运行中

  **方式 B: Docker Compose**
  ```bash
  cd /opt/bom_check/deploy
  docker-compose -f docker-compose.prod.yml restart
  sleep 3
  docker-compose -f docker-compose.prod.yml ps
  ```
  - [ ] 所有容器已重启并运行中

  **方式 C: 手动启动**
  ```bash
  cd /opt/bom_check
  nohup python3 api_server.py > logs/api.log 2>&1 &
  nohup python3 -m sync.sync_engine > logs/sync.log 2>&1 &
  ```
  - [ ] API 服务已启动
  - [ ] 同步服务已启动

### 步骤 9: 验证服务状态

- [ ] **检查 API 服务**
  ```bash
  curl -s http://localhost:5000/health || echo "API 服务检查失败"
  ```
  - [ ] API 服务响应正常

- [ ] **检查日志文件**
  ```bash
  tail -20 /opt/bom_check/logs/bom_check.log
  ```
  - [ ] 无明显错误信息
  - [ ] 查看最近 20 行日志

- [ ] **检查错误日志**
  ```bash
  grep -i "error\|exception\|failed" /opt/bom_check/logs/bom_check.log | tail -10
  ```
  - [ ] 无错误信息（或查看详细错误）

- [ ] **查看完整日志**
  ```bash
  tail -f /opt/bom_check/logs/bom_check.log
  ```
  （按 Ctrl+C 退出）
  - [ ] 服务运行日志正常

---

## 🧪 功能测试

### 步骤 10: 测试新增功能

- [ ] **测试 VR100 规则（子编码位置号校验）**

  1. 准备测试文件：
     ```bash
     cat > /tmp/test_vr100.py << 'EOF'
from validator.enhanced_rules import ChildCodePositionMatchRule

rule = ChildCodePositionMatchRule()
# 测试1: 正确的位置号
result1 = rule.validate("RED-00001", ["R001"])
print(f"Test 1 (RED-00001, R001): {result1}")

# 测试2: 错误的位置号
result2 = rule.validate("RED-00001", ["X001"])
print(f"Test 2 (RED-00001, X001): {result2}")
EOF
     cd /opt/bom_check && python3 /tmp/test_vr100.py
     ```
  - [ ] 测试 1 通过（无错误）
  - [ ] 测试 2 返回错误（预期行为）

- [ ] **测试数据校验流程**
  ```bash
  cd /opt/bom_check
  python3 bom_validator.py --test
  ```
  - [ ] 校验流程正常运行
  - [ ] 生成了报告文件

- [ ] **检查报告文件**
  ```bash
  ls -lh /opt/bom_check/reports/
  ```
  - [ ] 最近生成的报告文件存在

---

## 📊 性能检查

### 步骤 11: 系统性能验证

- [ ] **检查服务器资源使用**
  ```bash
  top -bn1 | head -20
  free -h
  df -h
  ```
  - [ ] CPU 使用率 < 80%
  - [ ] 内存使用率 < 80%
  - [ ] 磁盘使用率 < 80%

- [ ] **检查进程状态**
  ```bash
  ps aux | grep -E "python3|java|mysql"
  ```
  - [ ] API 进程正在运行
  - [ ] 数据库进程正在运行

---

## 🔄 异常处理

### 如果出现问题

- [ ] **收集诊断信息**
  ```bash
  # 保存完整日志
  cp /opt/bom_check/logs/bom_check.log /tmp/bom_error_$(date +%s).log
  
  # 保存系统信息
  uname -a > /tmp/system_info.txt
  python3 --version >> /tmp/system_info.txt
  pip list >> /tmp/system_info.txt
  ```

- [ ] **尝试故障排查**
  - [ ] 检查错误消息的完整内容
  - [ ] 查看服务日志中的关键错误
  - [ ] 验证环境变量是否正确设置

- [ ] **回滚方案**（如需要）
  ```bash
  cd /opt/bom_check
  git status
  git log --oneline | head -10
  git revert <commit-hash>  # 如果使用了 Git
  systemctl restart bom-api bom-sync
  ```

---

## ✨ 完成确认

- [ ] **所有步骤已完成**
  - [ ] 文件上传成功
  - [ ] 服务已重启
  - [ ] 功能已验证
  - [ ] 无错误信息

- [ ] **部署时间记录**
  - 开始时间: _______________
  - 结束时间: _______________
  - 总耗时: _______________

- [ ] **备注**
  ```
  
  
  
  ```

---

**检查清单完成时间**: _______________  
**检查人员**: _______________  
**是否成功**: ☐ 是  ☐ 否

