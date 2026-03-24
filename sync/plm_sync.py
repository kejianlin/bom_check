#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PLM数据同步主程序
用于从PLM生产数据库同步数据到只读同步库
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.sync_engine import SyncEngine
from utils.logger import get_default_logger

logger = get_default_logger()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PLM数据同步工具')
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental'],
        default='incremental',
        help='同步模式: full=全量同步, incremental=增量同步'
    )
    parser.add_argument(
        '--tables',
        nargs='+',
        help='指定要同步的表名，不指定则同步所有表'
    )
    parser.add_argument(
        '--init',
        action='store_true',
        help='初始化同步数据库'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示同步统计信息'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='统计最近N天的同步信息'
    )
    
    args = parser.parse_args()
    
    load_dotenv()
    
    logger.info("="*60)
    logger.info("PLM数据同步程序启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        sync_engine = SyncEngine()
        
        if args.init:
            logger.info("执行数据库初始化...")
            if sync_engine.initialize_sync_database():
                logger.info("数据库初始化成功")
            else:
                logger.error("数据库初始化失败")
                return 1
        
        if args.stats:
            logger.info(f"获取最近 {args.days} 天的同步统计...")
            stats = sync_engine.get_sync_statistics(args.days)
            
            if 'error' in stats:
                logger.error(f"获取统计信息失败: {stats['error']}")
            else:
                print("\n" + "="*80)
                print(f"同步统计信息（最近{stats['period_days']}天）")
                print("="*80)
                
                for stat in stats['statistics']:
                    print(f"\n表名: {stat['table_name']}")
                    print(f"  同步次数: {stat['sync_count']}")
                    print(f"  同步记录数: {stat['total_records']}")
                    print(f"  平均耗时: {stat['avg_duration']}秒")
                    print(f"  最后同步: {stat['last_sync_time']}")
                    print(f"  成功次数: {stat['success_count']}")
                    print(f"  失败次数: {stat['failed_count']}")
            
            return 0
        
        logger.info("测试数据库连接...")
        if not sync_engine.db_helper.test_connection('plm_production'):
            logger.error("无法连接到PLM生产数据库")
            return 1
        
        if not sync_engine.db_helper.test_connection('plm_sync'):
            logger.error("无法连接到PLM同步数据库")
            return 1
        
        logger.info("数据库连接测试成功")
        
        if args.tables:
            for table_name in args.tables:
                result = sync_engine.sync_table(table_name, args.mode)
                print(f"\n表 {table_name} 同步结果: {result}")
        else:
            summary = sync_engine.sync_all_tables(args.mode)
            
            print("\n" + "="*80)
            print("同步汇总")
            print("="*80)
            print(f"总表数: {summary['total_tables']}")
            print(f"成功: {summary['success_tables']}")
            print(f"失败: {len(summary['failed_tables'])}")
            print(f"总记录数: {summary['total_records']}")
            print(f"总耗时: {summary['duration']:.2f}秒")
            
            if summary['failed_tables']:
                print(f"\n失败的表: {', '.join(summary['failed_tables'])}")
        
        logger.info("同步程序执行完成")
        return 0
        
    except Exception as e:
        logger.error(f"同步程序执行异常: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
