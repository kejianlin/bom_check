#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出PLM数据到Excel
用于数据分析和手工核对
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_helper import DatabaseHelper
from utils.logger import get_default_logger
from sqlalchemy import text

logger = get_default_logger()


def export_materials(db_helper: DatabaseHelper, output_file: str):
    """导出物料数据"""
    logger.info("导出物料数据...")
    
    try:
        session = db_helper.get_session('plm_sync')
        query = text("""
            SELECT 
                material_code as '物料编码',
                material_name as '物料名称',
                specification as '规格型号',
                category as '类别',
                unit as '单位',
                status as '状态',
                supplier_code as '供应商编码',
                version as '版本',
                create_time as '创建时间',
                update_time as '更新时间'
            FROM materials
            ORDER BY material_code
        """)
        
        df = pd.read_sql(query, session.bind)
        session.close()
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='物料清单', index=False)
        
        logger.info(f"物料数据已导出: {len(df)} 条记录 -> {output_file}")
        return len(df)
        
    except Exception as e:
        logger.error(f"导出物料数据失败: {str(e)}")
        return 0


def export_all_data(db_helper: DatabaseHelper, output_file: str):
    """导出所有PLM数据到一个Excel文件（多个Sheet）"""
    logger.info("导出所有PLM数据...")
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            session = db_helper.get_session('plm_sync')
            
            queries = {
                '物料清单': """
                    SELECT 
                        material_code as '物料编码',
                        material_name as '物料名称',
                        specification as '规格型号',
                        category as '类别',
                        unit as '单位',
                        status as '状态',
                        supplier_code as '供应商编码',
                        version as '版本'
                    FROM materials
                    ORDER BY material_code
                """,
                '供应商清单': """
                    SELECT 
                        supplier_code as '供应商编码',
                        supplier_name as '供应商名称',
                        contact as '联系人',
                        phone as '电话',
                        email as '邮箱',
                        status as '状态',
                        certification as '认证'
                    FROM suppliers
                    ORDER BY supplier_code
                """,
                '单位清单': """
                    SELECT 
                        unit_code as '单位编码',
                        unit_name as '单位名称',
                        unit_type as '单位类型',
                        conversion_factor as '换算系数',
                        base_unit as '基准单位'
                    FROM units
                    ORDER BY unit_code
                """,
                '同步日志': """
                    SELECT 
                        sync_time as '同步时间',
                        sync_type as '同步类型',
                        table_name as '表名',
                        records_synced as '同步记录数',
                        status as '状态',
                        duration_seconds as '耗时(秒)'
                    FROM sync_logs
                    ORDER BY sync_time DESC
                    LIMIT 1000
                """
            }
            
            total_records = 0
            
            for sheet_name, query in queries.items():
                try:
                    df = pd.read_sql(text(query), session.bind)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"  - {sheet_name}: {len(df)} 条记录")
                    total_records += len(df)
                except Exception as e:
                    logger.error(f"导出 {sheet_name} 失败: {str(e)}")
            
            session.close()
        
        logger.info(f"所有数据已导出: {total_records} 条记录 -> {output_file}")
        return total_records
        
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        return 0


def export_statistics(db_helper: DatabaseHelper, output_file: str, days: int = 30):
    """导出统计数据"""
    logger.info(f"导出最近{days}天的统计数据...")
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            session = db_helper.get_session('plm_sync')
            
            sync_stats_query = text(f"""
                SELECT 
                    DATE(sync_time) as '日期',
                    table_name as '表名',
                    COUNT(*) as '同步次数',
                    SUM(records_synced) as '同步记录数',
                    AVG(duration_seconds) as '平均耗时(秒)',
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as '成功次数',
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as '失败次数'
                FROM sync_logs
                WHERE sync_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                GROUP BY DATE(sync_time), table_name
                ORDER BY DATE(sync_time) DESC, table_name
            """)
            
            df_sync = pd.read_sql(sync_stats_query, session.bind)
            df_sync.to_excel(writer, sheet_name='同步统计', index=False)
            
            session.close()
        
        logger.info(f"统计数据已导出: {output_file}")
        
    except Exception as e:
        logger.error(f"导出统计数据失败: {str(e)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='导出PLM数据到Excel')
    parser.add_argument(
        '--output',
        '-o',
        help='输出文件路径（默认：exports/plm_data_YYYYMMDD.xlsx）'
    )
    parser.add_argument(
        '--type',
        '-t',
        choices=['materials', 'all', 'stats'],
        default='all',
        help='导出类型: materials=仅物料, all=所有表, stats=统计信息'
    )
    parser.add_argument(
        '--days',
        '-d',
        type=int,
        default=30,
        help='统计天数（仅对stats类型有效）'
    )
    
    args = parser.parse_args()
    
    load_dotenv()
    
    logger.info("="*60)
    logger.info("PLM数据导出程序启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if args.output:
            output_file = args.output
        else:
            export_dir = Path('exports')
            export_dir.mkdir(exist_ok=True)
            
            if args.type == 'materials':
                output_file = export_dir / f"materials_{timestamp}.xlsx"
            elif args.type == 'stats':
                output_file = export_dir / f"statistics_{timestamp}.xlsx"
            else:
                output_file = export_dir / f"plm_data_{timestamp}.xlsx"
        
        db_helper = DatabaseHelper()
        
        logger.info("测试数据库连接...")
        if not db_helper.test_connection('plm_sync'):
            logger.error("无法连接到同步数据库")
            return 1
        
        if args.type == 'materials':
            records = export_materials(db_helper, str(output_file))
        elif args.type == 'stats':
            export_statistics(db_helper, str(output_file), args.days)
            records = 0
        else:
            records = export_all_data(db_helper, str(output_file))
        
        print("\n" + "="*80)
        print("导出完成")
        print("="*80)
        if records > 0:
            print(f"总记录数: {records}")
        print(f"输出文件: {output_file}")
        print("="*80)
        
        return 0
        
    except Exception as e:
        logger.error(f"导出程序异常: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
