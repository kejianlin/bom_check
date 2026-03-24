#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动创建MySQL同步表
从Oracle表结构自动生成MySQL表
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.db_helper import DatabaseHelper
from sqlalchemy import inspect, text
from utils.logger import get_default_logger

logger = get_default_logger()


def oracle_to_mysql_type(oracle_type: str, is_primary_key: bool = False) -> str:
    """
    Oracle类型转MySQL类型
    
    Args:
        oracle_type: Oracle数据类型
        is_primary_key: 是否为主键
    
    Returns:
        MySQL数据类型
    """
    oracle_type = str(oracle_type).upper()
    
    # VARCHAR/CHAR类型
    if 'VARCHAR' in oracle_type or 'CHAR' in oracle_type:
        if '(' in oracle_type:
            size = int(oracle_type.split('(')[1].split(')')[0])
            if is_primary_key:
                # 主键最大255
                return f'VARCHAR({min(size, 255)})'
            elif size > 500:
                # 大字段用TEXT避免行大小限制
                return 'TEXT'
            elif size > 255:
                return 'VARCHAR(500)'
            else:
                return f'VARCHAR({size})'
        else:
            return 'VARCHAR(255)' if is_primary_key else 'VARCHAR(100)'
    
    # NUMBER类型
    elif 'NUMBER' in oracle_type:
        if ',' in oracle_type:
            return 'DECIMAL(18,6)'
        else:
            return 'BIGINT'
    
    # 日期类型
    elif 'DATE' in oracle_type or 'TIMESTAMP' in oracle_type:
        return 'DATETIME'
    
    # 大对象类型
    elif 'CLOB' in oracle_type:
        return 'LONGTEXT'
    elif 'BLOB' in oracle_type:
        return 'LONGBLOB'
    
    # 默认
    else:
        return 'VARCHAR(255)' if is_primary_key else 'TEXT'


def generate_create_table_sql(table_name: str, inspector) -> str:
    """
    生成建表SQL
    
    Args:
        table_name: 表名
        inspector: SQLAlchemy inspector对象
    
    Returns:
        CREATE TABLE SQL语句
    """
    try:
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = pk_constraint['constrained_columns'] if pk_constraint else []
        
        sql_parts = []
        sql_parts.append(f"-- {table_name}表")
        sql_parts.append(f"DROP TABLE IF EXISTS `{table_name}`;")
        sql_parts.append(f"CREATE TABLE `{table_name}` (")
        
        col_defs = []
        
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            is_pk = col_name in pk_columns
            
            mysql_type = oracle_to_mysql_type(col_type, is_pk)
            
            # 主键必须NOT NULL
            if is_pk:
                nullable = ' NOT NULL'
            elif 'TEXT' in mysql_type or 'BLOB' in mysql_type:
                nullable = ''
            else:
                nullable = '' if col['nullable'] else ' NOT NULL'
            
            col_defs.append(f"    `{col_name}` {mysql_type}{nullable}")
        
        # 添加主键
        if pk_columns:
            pk_cols = '`, `'.join(pk_columns)
            col_defs.append(f"    PRIMARY KEY (`{pk_cols}`)")
        
        sql_parts.append(',\n'.join(col_defs))
        sql_parts.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;")
        sql_parts.append("")
        
        return '\n'.join(sql_parts)
        
    except Exception as e:
        logger.error(f"生成表 {table_name} 的SQL失败: {e}")
        return f"-- 错误: 无法生成表 {table_name}: {e}\n"


def create_tables_from_oracle(tables: list = None):
    """
    从Oracle创建MySQL表
    
    Args:
        tables: 要创建的表名列表，None表示从配置文件读取
    """
    logger.info("开始从Oracle生成MySQL表结构...")
    
    # 获取数据库连接
    db = DatabaseHelper()
    source_engine = db.get_engine('plm_production')
    target_engine = db.get_engine('plm_sync')
    
    inspector = inspect(source_engine)
    
    # 如果未指定表，从配置文件读取
    if tables is None:
        import yaml
        with open('config/sync_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        tables = [name for name, cfg in config['tables'].items() if cfg.get('enabled')]
    
    logger.info(f"将创建 {len(tables)} 个表: {', '.join(tables)}")
    
    # 生成SQL
    all_sql = ["USE plm_sync_db;\n", "SET NAMES utf8mb4;\n"]
    
    for table_name in tables:
        logger.info(f"处理表: {table_name}")
        sql = generate_create_table_sql(table_name, inspector)
        all_sql.append(sql)
    
    full_sql = '\n'.join(all_sql)
    
    # 保存到文件
    output_file = Path('deploy/mysql/auto_generated_tables.sql')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_sql)
    
    logger.info(f"SQL已保存到: {output_file}")
    
    # 询问是否执行
    print("\n生成的SQL:")
    print("="*60)
    print(full_sql)
    print("="*60)
    
    response = input("\n是否立即执行SQL创建表? (y/n): ")
    
    if response.lower() == 'y':
        logger.info("执行SQL创建表...")
        try:
            with target_engine.begin() as conn:
                for statement in full_sql.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        conn.execute(text(statement))
            
            logger.info("✅ 表创建成功！")
            
            # 验证
            with target_engine.connect() as conn:
                for table_name in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    logger.info(f"  {table_name}: {count} 行")
            
        except Exception as e:
            logger.error(f"❌ 执行SQL失败: {e}")
            return False
    else:
        logger.info("已跳过执行，请手动执行SQL文件")
    
    return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从Oracle自动创建MySQL表')
    parser.add_argument('--tables', nargs='+', help='指定要创建的表名')
    parser.add_argument('--execute', action='store_true', help='自动执行SQL（不询问）')
    
    args = parser.parse_args()
    
    try:
        create_tables_from_oracle(args.tables)
        return 0
    except Exception as e:
        logger.error(f"创建表失败: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
