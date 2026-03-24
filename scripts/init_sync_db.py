#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化PLM只读同步库
创建必要的数据库表结构
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.plm_models import Base
from utils.db_helper import DatabaseHelper
from utils.logger import get_default_logger

logger = get_default_logger()


def main():
    """主函数"""
    load_dotenv()
    
    logger.info("="*60)
    logger.info("开始初始化PLM只读同步库")
    logger.info("="*60)
    
    try:
        db_helper = DatabaseHelper()
        
        logger.info("测试数据库连接...")
        if not db_helper.test_connection('plm_sync'):
            logger.error("无法连接到同步数据库，请检查配置")
            return 1
        
        logger.info("数据库连接成功")
        
        logger.info("创建数据库表结构...")
        engine = db_helper.get_engine('plm_sync')
        Base.metadata.create_all(engine)
        
        logger.info("数据库表结构创建成功")
        
        logger.info("\n创建的表:")
        logger.info("  - materials (物料主表)")
        logger.info("  - material_attributes (物料属性表)")
        logger.info("  - bom_structure (BOM结构表)")
        logger.info("  - suppliers (供应商表)")
        logger.info("  - units (计量单位表)")
        logger.info("  - sync_logs (同步日志表)")
        
        logger.info("\n" + "="*60)
        logger.info("初始化完成！")
        logger.info("下一步: 执行数据同步")
        logger.info("  python sync/plm_sync.py --mode full")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
