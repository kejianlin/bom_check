# BOM Check 项目上传脚本
# 使用方法: .\upload_to_server.ps1 [-Password "your_password"]

param(
    [string]$ServerHost = "119.136.22.122",
    [int]$ServerPort = 2232,
    [string]$ServerUser = "root",
    [string]$RemotePath = "/opt/bom_check",
    [string]$Password = ""
)

$LocalPath = "D:\work\project\bom_check"
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Green
Write-Host "BOM Check 项目上传工具" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "本地路径: $LocalPath"
Write-Host "服务器: $ServerUser@$ServerHost:$RemotePath"
Write-Host "端口: $ServerPort"
Write-Host ""

# 检查 SCP 是否可用
$scpPath = Get-Command scp -ErrorAction SilentlyContinue
if (-not $scpPath) {
    Write-Host "❌ 错误: 未找到 scp 命令。请确保 OpenSSH 已安装。" -ForegroundColor Red
    Write-Host "   可以在 Git Bash 或 Windows 内置的 OpenSSH 中使用。"
    exit 1
}

# 获取需要上传的文件
Write-Host "📂 扫描项目文件..." -ForegroundColor Yellow
$totalFiles = (Get-ChildItem -Path $LocalPath -Recurse -File | Measure-Object).Count
Write-Host "   找到 $totalFiles 个文件"
Write-Host ""

# 确认上传
$confirm = Read-Host "确认上传这些文件到服务器? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "❌ 已取消上传" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "⏳ 正在上传文件..." -ForegroundColor Cyan

# 执行上传
try {
    # 方案 1: 使用密码（如果提供）
    if ($Password) {
        # 通过 plink (PuTTY) 处理密码
        Write-Host "使用 SSH 密钥或密码认证进行上传..."
        scp -P $ServerPort -r "$LocalPath" "$($ServerUser)@$($ServerHost):$RemotePath"
    } else {
        # 方案 2: 使用 SSH 密钥（推荐）
        Write-Host "使用 SSH 密钥进行上传..."
        Write-Host "请在 SSH 密钥认证窗口中完成认证"
        scp -P $ServerPort -r "$LocalPath" "$($ServerUser)@$($ServerHost):$RemotePath"
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ 上传成功!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 后续操作建议:" -ForegroundColor Cyan
        Write-Host "  1. 在服务器上重启服务"
        Write-Host "     ssh -p $ServerPort $ServerUser@$ServerHost"
        Write-Host "     cd $RemotePath"
        Write-Host "     python -m pip install -r requirements.txt"
        Write-Host "     systemctl restart bom-api"
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "❌ 上传失败，请检查网络连接和认证信息。" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host ""
    Write-Host "❌ 错误: $_" -ForegroundColor Red
    exit 1
}
