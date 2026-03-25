@echo off
REM BOM Check 项目上传脚本 (Windows Batch)
REM 使用前需要配置：
REM 1. 确保安装了 OpenSSH (Win10+内置，或使用 Git Bash)
REM 2. 配置 SSH 密钥或密码认证

setlocal enabledelayedexpansion

set SERVER_HOST=119.136.22.122
set SERVER_PORT=2232
set SERVER_USER=root
set REMOTE_PATH=/opt/bom_check
set LOCAL_PATH=D:\work\project\bom_check

cls
echo.
echo ========================================
echo BOM Check 项目上传工具 (Windows)
echo ========================================
echo.
echo 本地路径: %LOCAL_PATH%
echo 服务器: %SERVER_USER%@%SERVER_HOST%:%REMOTE_PATH%
echo 端口: %SERVER_PORT%
echo.

REM 检查 scp 命令
where scp >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 scp 命令
    echo.
    echo 请选择以下方式解决：
    echo 1. 如果使用 Git Bash: 通过 Git Bash 运行此脚本
    echo 2. 如果使用 Windows 10+: 安装 OpenSSH Optional Feature
    echo    Settings ^> Apps ^> Apps and Features ^> Optional Features ^> Add OpenSSH Client
    echo 3. 或者使用 PowerShell 脚本: upload_to_server.ps1
    echo.
    pause
    exit /b 1
)

echo 📂 正在计算文件数量...
for /r "%LOCAL_PATH%" %%i in (*) do set /a file_count+=1
echo    找到 !file_count! 个文件
echo.

set /p confirm="确认上传这些文件到服务器? (y/n): "
if /i not "%confirm%"=="y" (
    echo ❌ 已取消上传
    exit /b 0
)

echo.
echo ⏳ 正在上传文件...
echo.

REM 使用 -r 递归上传整个目录
scp -P %SERVER_PORT% -r "%LOCAL_PATH%" "%SERVER_USER%@%SERVER_HOST%:%REMOTE_PATH%\.."

if errorlevel 1 (
    echo.
    echo ❌ 上传失败
    echo.
    echo 可能的原因：
    echo - SSH 连接失败 (检查网络和防火墙)
    echo - 认证失败 (检查密码或 SSH 密钥)
    echo - 权限不足 (检查远程服务器权限)
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ 上传成功!
    echo.
    echo 📋 后续操作建议:
    echo.
    echo 1. 连接到服务器进行验证：
    echo    ssh -p %SERVER_PORT% %SERVER_USER%@%SERVER_HOST%
    echo.
    echo 2. 检查文件完整性：
    echo    cd %REMOTE_PATH% ^& ls -la
    echo.
    echo 3. 重启应用服务：
    echo    systemctl restart bom-api
    echo    systemctl restart bom-sync
    echo.
    pause
    exit /b 0
)
