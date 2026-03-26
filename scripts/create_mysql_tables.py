#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动创建MySQL同步表
从Oracle表结构自动生成MySQL表
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
import yaml

from utils.db_helper import DatabaseHelper
from utils.logger import get_default_logger

logger = get_default_logger()


TEXT_FALLBACK_COLUMNS = {
    "ITEMDESC",
    "NOTE",
    "SPEC",
    "APPSTD",
    "ITEMDESCSUPPLEMENT",
    "LASTITEMDESC",
    "SALedesc".upper(),
    "MAKEPRODUCT",
    "PCBDESCPOS",
    "SITEMCODE",
}


def split_sql_statements(sql: str) -> List[str]:
    """去掉注释后再拆分SQL，避免注释和DROP语句被一起跳过。"""
    cleaned_lines = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        cleaned_lines.append(line)

    cleaned_sql = "\n".join(cleaned_lines)
    return [statement.strip() for statement in cleaned_sql.split(";") if statement.strip()]


def normalize_identifier(name: str, case_mode: str = "preserve") -> str:
    """规范化标识符大小写。"""
    if case_mode == "lower":
        return name.lower()
    if case_mode == "upper":
        return name.upper()
    return name


def format_default_value(default_value: Any) -> str:
    """格式化Oracle默认值为MySQL默认值。"""
    if default_value is None:
        return ""

    value = str(default_value).strip()
    if not value:
        return ""

    normalized = value.upper()
    if normalized in {"SYSDATE", "SYSTIMESTAMP", "CURRENT_TIMESTAMP"}:
        return " DEFAULT CURRENT_TIMESTAMP"

    return f" DEFAULT {value}"


def is_wide_text_candidate(column_name: str, data_length: Any) -> bool:
    """判断列是否应在兼容模式下降级为TEXT，避免MySQL行大小超限。"""
    upper_name = str(column_name).upper()
    if upper_name in TEXT_FALLBACK_COLUMNS:
        return True

    if upper_name.startswith("STRDEF") or upper_name.startswith("ITEMDEF") or upper_name.startswith("CDEF"):
        return True

    if upper_name.startswith("CATNAME") or upper_name.startswith("PCBDOCNAME"):
        return True

    try:
        return data_length is not None and int(data_length) >= 256
    except Exception:
        return False


def oracle_to_mysql_type(column: Dict[str, Any], is_primary_key: bool = False,
                         strict_types: bool = False) -> str:
    """Oracle类型转MySQL类型。"""
    oracle_type = str(column["data_type"]).upper()
    data_length = column.get("data_length")
    data_precision = column.get("data_precision")
    data_scale = column.get("data_scale")
    column_name = column["column_name"]

    if oracle_type in {"VARCHAR2", "NVARCHAR2", "VARCHAR", "CHAR", "NCHAR"}:
        size = int(data_length or 255)
        if strict_types:
            return f"VARCHAR({max(1, size)})"
        if is_primary_key:
            return f"VARCHAR({min(max(1, size), 255)})"
        if is_wide_text_candidate(column_name, size):
            return "TEXT"
        return f"VARCHAR({max(1, size)})"

    if oracle_type == "NUMBER":
        if data_precision is None and data_scale is None:
            return "DECIMAL(38,10)" if strict_types else "BIGINT"

        scale = int(data_scale or 0)
        precision = int(data_precision or 38)
        if scale > 0:
            return f"DECIMAL({precision},{scale})"
        if strict_types:
            return f"DECIMAL({precision},0)"
        if precision <= 9:
            return "INT"
        if precision <= 18:
            return "BIGINT"
        return f"DECIMAL({precision},0)"

    if oracle_type in {"FLOAT", "BINARY_FLOAT"}:
        return "FLOAT"
    if oracle_type == "BINARY_DOUBLE":
        return "DOUBLE"

    if oracle_type == "DATE":
        return "DATETIME"
    if "TIMESTAMP" in oracle_type:
        return "DATETIME"

    if oracle_type in {"CLOB", "NCLOB", "LONG"}:
        return "LONGTEXT"
    if oracle_type in {"BLOB", "RAW", "LONG RAW"}:
        return "LONGBLOB"

    return "VARCHAR(255)" if is_primary_key else "TEXT"


def get_oracle_columns(source_engine, table_name: str) -> List[Dict[str, Any]]:
    """直接读取Oracle列元数据，保留原始大写字段名。"""
    query = text("""
        SELECT
            column_name,
            data_type,
            data_length,
            data_precision,
            data_scale,
            nullable,
            data_default,
            column_id
        FROM user_tab_columns
        WHERE table_name = :table_name
        ORDER BY column_id
    """)

    with source_engine.connect() as conn:
        rows = conn.execute(query, {"table_name": table_name.upper()}).mappings().all()

    return [dict(row) for row in rows]


def get_oracle_primary_keys(source_engine, table_name: str) -> List[str]:
    """读取Oracle主键列。"""
    query = text("""
        SELECT cols.column_name
        FROM user_constraints cons
        JOIN user_cons_columns cols
          ON cons.constraint_name = cols.constraint_name
        WHERE cons.table_name = :table_name
          AND cons.constraint_type = 'P'
        ORDER BY cols.position
    """)

    with source_engine.connect() as conn:
        rows = conn.execute(query, {"table_name": table_name.upper()}).fetchall()

    return [row[0] for row in rows]


def load_sync_config() -> Dict[str, Any]:
    """加载同步配置。"""
    with open("config/sync_config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def filter_columns_by_whitelist(columns: List[Dict[str, Any]], include_columns: List[str]) -> List[Dict[str, Any]]:
    """按白名单筛选列，保持Oracle原始顺序。"""
    if not include_columns:
        return columns

    whitelist = {column.upper() for column in include_columns}
    filtered_columns = [column for column in columns if column["column_name"].upper() in whitelist]

    missing_columns = sorted(whitelist - {column["column_name"].upper() for column in columns})
    if missing_columns:
        logger.warning(f"白名单中有 {len(missing_columns)} 个字段在Oracle表中不存在: {', '.join(missing_columns[:10])}")

    return filtered_columns


def generate_create_table_sql(table_name: str, source_engine,
                              case_mode: str = "preserve",
                              strict_types: bool = False,
                              include_columns: List[str] = None) -> str:
    """生成单表建表SQL。"""
    try:
        columns = get_oracle_columns(source_engine, table_name)
        columns = filter_columns_by_whitelist(columns, include_columns or [])
        pk_columns = get_oracle_primary_keys(source_engine, table_name)
        if include_columns:
            include_set = {column.upper() for column in include_columns}
            pk_columns = [column for column in pk_columns if column.upper() in include_set]
        output_table_name = normalize_identifier(table_name, case_mode)

        sql_parts = []
        sql_parts.append(f"-- {table_name}表")
        sql_parts.append(f"DROP TABLE IF EXISTS `{output_table_name}`;")
        sql_parts.append(f"CREATE TABLE `{output_table_name}` (")

        col_defs = []

        for col in columns:
            col_name = col["column_name"]
            output_col_name = normalize_identifier(col_name, case_mode)
            is_pk = col_name in pk_columns
            mysql_type = oracle_to_mysql_type(col, is_pk, strict_types)

            if is_pk:
                nullable = " NOT NULL"
            elif "TEXT" in mysql_type or "BLOB" in mysql_type:
                nullable = ""
            else:
                nullable = "" if col.get("nullable") == "Y" else " NOT NULL"

            default_clause = ""
            if not is_pk and "TEXT" not in mysql_type and "BLOB" not in mysql_type:
                default_clause = format_default_value(col.get("data_default"))

            col_defs.append(f"    `{output_col_name}` {mysql_type}{nullable}{default_clause}")

        if pk_columns:
            pk_cols = "`, `".join(normalize_identifier(col, case_mode) for col in pk_columns)
            col_defs.append(f"    PRIMARY KEY (`{pk_cols}`)")

        sql_parts.append(",\n".join(col_defs))
        sql_parts.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;")
        sql_parts.append("")

        return "\n".join(sql_parts)

    except Exception as e:
        logger.error(f"生成表 {table_name} 的SQL失败: {e}")
        return f"-- 错误: 无法生成表 {table_name}: {e}\n"


def create_tables_from_oracle(tables: List[str] = None, case_mode: str = "preserve",
                              strict_types: bool = False, execute_sql: bool = False):
    """从Oracle创建MySQL表。"""
    logger.info("开始从Oracle生成MySQL表结构...")

    db = DatabaseHelper()
    source_engine = db.get_engine("plm_production")
    target_engine = db.get_engine("plm_sync")

    config = load_sync_config()

    if tables is None:
        tables = [name for name, cfg in config["tables"].items() if cfg.get("enabled")]

    logger.info(f"将创建 {len(tables)} 个表: {', '.join(tables)}")

    all_sql = ["USE plm_sync_db;\n", "SET NAMES utf8mb4;\n"]

    for table_name in tables:
        logger.info(f"处理表: {table_name}")
        table_config = config.get("tables", {}).get(table_name, {})
        include_columns = table_config.get("include_columns", [])
        if include_columns:
            logger.info(f"表 {table_name} 使用白名单字段生成，共 {len(include_columns)} 个字段")
        sql = generate_create_table_sql(
            table_name,
            source_engine,
            case_mode=case_mode,
            strict_types=strict_types,
            include_columns=include_columns,
        )
        all_sql.append(sql)

    full_sql = "\n".join(all_sql)

    output_file = Path("deploy/mysql/auto_generated_tables.sql")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_sql)

    logger.info(f"SQL已保存到: {output_file}")

    print("\n生成的SQL:")
    print("=" * 60)
    print(full_sql)
    print("=" * 60)

    should_execute = execute_sql
    if not execute_sql:
        response = input("\n是否立即执行SQL创建表? (y/n): ")
        should_execute = response.lower() == "y"

    if should_execute:
        logger.info("执行SQL创建表...")
        try:
            with target_engine.begin() as conn:
                for statement in split_sql_statements(full_sql):
                    conn.execute(text(statement))

            logger.info("✅ 表创建成功！")
        except Exception as e:
            logger.error(f"❌ 执行SQL失败: {e}")
            return False
    else:
        logger.info("已跳过执行，请手动执行SQL文件")

    return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="从Oracle自动创建MySQL表")
    parser.add_argument("--tables", nargs="+", help="指定要创建的表名")
    parser.add_argument("--execute", action="store_true", help="自动执行SQL（不询问）")
    parser.add_argument(
        "--name-case",
        choices=["preserve", "lower", "upper"],
        default="preserve",
        help="生成的表名/字段名大小写模式，preserve表示保持Oracle原样",
    )
    parser.add_argument(
        "--strict-types",
        action="store_true",
        help="尽量严格保留Oracle长度和精度；不启用时会对超宽表做MySQL兼容映射",
    )

    args = parser.parse_args()

    try:
        create_tables_from_oracle(
            args.tables,
            case_mode=args.name_case,
            strict_types=args.strict_types,
            execute_sql=args.execute,
        )
        return 0
    except Exception as e:
        logger.error(f"创建表失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
