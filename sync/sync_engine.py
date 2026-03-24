import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from models.plm_models import Base, SyncLog
from utils.db_helper import DatabaseHelper
from utils.logger import get_default_logger
import os
from dotenv import load_dotenv

# 确保环境变量已加载
load_dotenv()

logger = get_default_logger()


class SyncEngine:
    """数据同步引擎"""
    
    def __init__(self, config_path: str = "config/sync_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.db_helper = DatabaseHelper()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载同步配置"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def initialize_sync_database(self):
        """初始化同步数据库（创建表结构）"""
        logger.info("开始初始化同步数据库...")
        
        try:
            engine = self.db_helper.get_engine('plm_sync')
            Base.metadata.create_all(engine)
            logger.info("同步数据库表结构创建成功")
            return True
        except Exception as e:
            logger.error(f"初始化同步数据库失败: {str(e)}")
            return False
    
    def sync_table(self, table_name: str, mode: str = 'incremental') -> Dict[str, Any]:
        """同步单个表"""
        logger.info(f"开始同步表: {table_name}, 模式: {mode}")
        start_time = datetime.now()
        
        try:
            table_config = self.config['tables'].get(table_name, {})
            if not table_config.get('enabled', False):
                logger.warning(f"表 {table_name} 未启用同步")
                return {'status': 'skipped', 'message': '未启用'}
            
            source_engine = self.db_helper.get_engine('plm_production')
            target_engine = self.db_helper.get_engine('plm_sync')
            
            primary_key = table_config.get('primary_key', 'id')
            incremental_field = table_config.get('incremental_field')
            
            where_clause = ""
            if mode == 'incremental' and incremental_field:
                last_sync_time = self._get_last_sync_time(table_name)
                if last_sync_time:
                    where_clause = f"WHERE {incremental_field} > '{last_sync_time}'"
            
            query = f"SELECT * FROM {table_name} {where_clause}"
            
            with source_engine.connect() as source_conn:
                result = source_conn.execute(text(query))
                columns = result.keys()
                rows = result.fetchall()
                
                logger.info(f"从源数据库读取 {len(rows)} 条记录")
                
                if len(rows) == 0:
                    logger.info(f"表 {table_name} 没有需要同步的数据")
                    return {'status': 'success', 'records': 0, 'message': '无新数据'}
                
                synced_count = 0
                batch_size = self.config['sync_strategy'].get('batch_size', 1000)
                
                # 获取目标数据库类型
                db_config = self.db_helper.config.get('plm_sync', {})
                db_type = db_config.get('type', 'mysql').lower()
                
                with target_engine.begin() as target_conn:
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        
                        for row in batch:
                            row_dict = dict(zip(columns, row))
                            
                            placeholders = ', '.join([f':{col}' for col in columns])
                            columns_str = ', '.join(columns)
                            
                            update_set = ', '.join([f'{col}=:{col}' for col in columns if col != primary_key])
                            
                            if db_type == 'postgresql':
                                upsert_query = f"""
                                    INSERT INTO {table_name} ({columns_str})
                                    VALUES ({placeholders})
                                    ON CONFLICT ({primary_key}) DO UPDATE SET {update_set}
                                """
                            else:
                                # MySQL/MariaDB
                                upsert_query = f"""
                                    INSERT INTO {table_name} ({columns_str})
                                    VALUES ({placeholders})
                                    ON DUPLICATE KEY UPDATE {update_set}
                                """
                            
                            try:
                                target_conn.execute(text(upsert_query), row_dict)
                                synced_count += 1
                            except Exception as e:
                                logger.error(f"同步记录失败 {primary_key}={row_dict.get(primary_key)}: {str(e)}")
                        
                        logger.info(f"已同步 {synced_count}/{len(rows)} 条记录")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self._log_sync_result(
                table_name=table_name,
                sync_type=mode,
                records_synced=synced_count,
                status='success',
                duration=duration
            )
            
            logger.info(f"表 {table_name} 同步完成，共 {synced_count} 条记录，耗时 {duration:.2f} 秒")
            
            return {
                'status': 'success',
                'records': synced_count,
                'duration': duration
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"同步表 {table_name} 失败: {error_msg}")
            
            self._log_sync_result(
                table_name=table_name,
                sync_type=mode,
                records_synced=0,
                status='failed',
                error_message=error_msg,
                duration=duration
            )
            
            return {
                'status': 'failed',
                'error': error_msg,
                'duration': duration
            }
    
    def sync_all_tables(self, mode: str = 'incremental') -> Dict[str, Any]:
        """同步所有表"""
        logger.info(f"开始同步所有表，模式: {mode}")
        start_time = datetime.now()
        
        results = {}
        total_records = 0
        failed_tables = []
        
        for table_name, table_config in self.config['tables'].items():
            if not table_config.get('enabled', False):
                continue
            
            result = self.sync_table(table_name, mode)
            results[table_name] = result
            
            if result['status'] == 'success':
                total_records += result.get('records', 0)
            else:
                failed_tables.append(table_name)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            'total_tables': len(results),
            'success_tables': len(results) - len(failed_tables),
            'failed_tables': failed_tables,
            'total_records': total_records,
            'duration': duration,
            'results': results
        }
        
        logger.info(f"所有表同步完成，共 {total_records} 条记录，耗时 {duration:.2f} 秒")
        
        return summary
    
    def _get_last_sync_time(self, table_name: str) -> Optional[str]:
        """获取表的最后同步时间"""
        try:
            session = self.db_helper.get_session('plm_sync')
            query = text("""
                SELECT MAX(sync_time) as last_sync
                FROM sync_logs
                WHERE table_name = :table_name AND status = 'success'
            """)
            result = session.execute(query, {'table_name': table_name}).fetchone()
            session.close()
            
            if result and result[0]:
                return result[0].strftime('%Y-%m-%d %H:%M:%S')
            return None
        except Exception as e:
            logger.warning(f"获取最后同步时间失败: {str(e)}")
            return None
    
    def _log_sync_result(self, table_name: str, sync_type: str, records_synced: int,
                         status: str, error_message: str = None, duration: float = 0):
        """记录同步结果"""
        try:
            session = self.db_helper.get_session('plm_sync')
            log = SyncLog(
                sync_time=datetime.now(),
                sync_type=sync_type,
                table_name=table_name,
                records_synced=records_synced,
                status=status,
                error_message=error_message,
                duration_seconds=duration
            )
            session.add(log)
            session.commit()
            session.close()
        except Exception as e:
            logger.error(f"记录同步日志失败: {str(e)}")
    
    def get_sync_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取同步统计信息"""
        try:
            session = self.db_helper.get_session('plm_sync')
            since_date = datetime.now() - timedelta(days=days)
            
            query = text("""
                SELECT 
                    table_name,
                    COUNT(*) as sync_count,
                    SUM(records_synced) as total_records,
                    AVG(duration_seconds) as avg_duration,
                    MAX(sync_time) as last_sync_time,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
                FROM sync_logs
                WHERE sync_time >= :since_date
                GROUP BY table_name
            """)
            
            result = session.execute(query, {'since_date': since_date})
            rows = result.fetchall()
            session.close()
            
            stats = []
            for row in rows:
                stats.append({
                    'table_name': row[0],
                    'sync_count': row[1],
                    'total_records': row[2],
                    'avg_duration': round(row[3], 2) if row[3] else 0,
                    'last_sync_time': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None,
                    'success_count': row[5],
                    'failed_count': row[6]
                })
            
            return {
                'period_days': days,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"获取同步统计失败: {str(e)}")
            return {'error': str(e)}
