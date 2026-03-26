#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境检查脚本
在部署前运行，检查系统环境是否满足要求
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    print(f"  当前版本: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3:
        print("  ❌ 错误: 需要Python 3.x")
        return False
    
    if version.minor < 6:
        print("  ❌ 错误: 需要Python 3.6或更高版本")
        return False
    
    if version.minor < 8:
        print("  ⚠️  警告: Python 3.6-3.7已不再维护，建议升级到3.8+")
        print("  ℹ️  将使用兼容模式（降级依赖包版本）")
    else:
        print("  ✅ Python版本符合要求")
    
    return True

def check_required_modules():
    """检查必需的Python模块"""
    print("\n检查必需模块...")
    required_modules = {
        'yaml': 'pyyaml',
        'dotenv': 'python-dotenv',
        'sqlalchemy': 'SQLAlchemy',
        'flask': 'Flask',
    }
    
    missing = []
    for module, package in required_modules.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} 未安装")
            missing.append(package)
    
    if missing:
        print(f"\n请安装缺失的包: pip install {' '.join(missing)}")
        return False
    
    return True

def check_database_drivers():
    """检查数据库驱动"""
    print("\n检查数据库驱动...")
    drivers = {
        'PyMySQL': 'pymysql',
        'oracledb': 'oracledb',
        'psycopg2': 'psycopg2',
    }
    
    for name, module in drivers.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ⚠️  {name} 未安装（如不使用该数据库可忽略）")
    
    return True

def check_config_files():
    """检查配置文件"""
    print("\n检查配置文件...")
    config_files = [
        'config/database.yaml',
        'config/sync_config.yaml',
        '.env.example',
    ]
    
    all_exist = True
    for file in config_files:
        path = Path(file)
        if path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} 不存在")
            all_exist = False
    
    # 检查.env文件
    if Path('.env').exists():
        print(f"  ✅ .env")
    else:
        print(f"  ⚠️  .env 不存在（请从.env.example复制并配置）")
    
    return all_exist

def check_directories():
    """检查必需的目录"""
    print("\n检查目录结构...")
    required_dirs = [
        'config',
        'models',
        'sync',
        'utils',
        'validator',
        'logs',
        'reports',
        'temp',
    ]
    
    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ⚠️  {dir_name}/ 不存在，将自动创建")
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"     已创建 {dir_name}/")
            except Exception as e:
                print(f"     ❌ 创建失败: {e}")
    
    return True

def check_oracle_client():
    """检查Oracle客户端（如果需要连接Oracle）"""
    print("\n检查Oracle Instant Client...")

    candidate_paths = []

    # 优先检查显式配置
    for env_name in ['ORACLE_CLIENT_LIB', 'ORACLE_HOME']:
        env_value = os.environ.get(env_name)
        if env_value:
            candidate_paths.append((env_name, env_value))

    # LD_LIBRARY_PATH 可能包含多个目录
    ld_library_path = os.environ.get('LD_LIBRARY_PATH')
    if ld_library_path:
        for path in ld_library_path.split(':'):
            if path:
                candidate_paths.append(('LD_LIBRARY_PATH', path))

    # 常见安装路径
    for path in [
        '/opt/oracle/instantclient_19_30',
        '/opt/oracle/instantclient_19_22',
        '/opt/oracle/instantclient_19_12',
        '/opt/oracle/instantclient_21_1',
        '/opt/oracle/instantclient_11_2',
    ]:
        candidate_paths.append(('default', path))

    found = False
    checked = set()
    for source, path in candidate_paths:
        normalized = str(path).strip()
        if not normalized or normalized in checked:
            continue
        checked.add(normalized)

        if os.path.exists(normalized):
            if source == 'default':
                print(f"  ✅ 找到Oracle客户端: {normalized}")
            else:
                print(f"  ✅ 找到Oracle客户端({source}): {normalized}")
            found = True
            break
    
    if not found:
        print(f"  ⚠️  未找到Oracle Instant Client")
        print(f"     如需连接Oracle 11g，请安装Oracle Instant Client")
        print(f"     下载地址: https://www.oracle.com/database/technologies/instant-client/downloads.html")
    
    return True

def main():
    """主函数"""
    load_dotenv()

    print("="*60)
    print("BOM检查系统 - 环境检查")
    print("="*60)
    
    checks = [
        ("Python版本", check_python_version),
        ("必需模块", check_required_modules),
        ("数据库驱动", check_database_drivers),
        ("配置文件", check_config_files),
        ("目录结构", check_directories),
        ("Oracle客户端", check_oracle_client),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 检查 {name} 时出错: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("检查结果汇总")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✅ 环境检查通过，可以开始部署！")
        return 0
    else:
        print("\n⚠️  部分检查未通过，请先解决上述问题")
        return 1

if __name__ == '__main__':
    sys.exit(main())
