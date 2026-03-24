#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库验证服务
用于验证BOM数据是否在数据库中存在
"""

from typing import Dict, Set, List, Optional
from sqlalchemy import text
from utils.db_helper import DatabaseHelper
from utils.logger import get_default_logger

logger = get_default_logger()


class DBValidator:
    """数据库验证器"""
    
    def __init__(self, db_name: str = "plm_sync"):
        """
        初始化数据库验证器
        
        Args:
            db_name: 数据库配置名称，默认使用plm_sync（MySQL同步库）
                    也可以使用plm_production（Oracle生产库）
        """
        self.db_helper = DatabaseHelper()
        self.db_name = db_name
        self._item_code_cache: Optional[Set[str]] = None
        self._parent_code_cache: Optional[Set[str]] = None
    
    def _load_item_codes(self) -> Set[str]:
        """
        从cpcitem表加载所有ITEMCODE
        
        Returns:
            ITEMCODE集合
        """
        if self._item_code_cache is not None:
            return self._item_code_cache
        
        try:
            logger.info("开始从cpcitem表加载ITEMCODE...")
            
            query = """
                SELECT ITEMCODE 
                FROM cpcitem 
                WHERE ITEMCODE IS NOT NULL
            """
            
            engine = self.db_helper.get_engine(self.db_name)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                item_codes = {row[0].strip() for row in result if row[0]}
            
            self._item_code_cache = item_codes
            logger.info(f"成功加载 {len(item_codes)} 个ITEMCODE")
            
            return item_codes
            
        except Exception as e:
            logger.error(f"加载ITEMCODE失败: {str(e)}")
            raise
    
    def check_item_code_exists(self, item_code: str) -> bool:
        """
        检查子编码是否存在于cpcitem表的ITEMCODE字段
        
        Args:
            item_code: 子编码
            
        Returns:
            是否存在
        """
        if not item_code:
            return False
        
        item_codes = self._load_item_codes()
        return item_code.strip() in item_codes
    
    def check_item_codes_batch(self, item_codes: List[str]) -> Dict[str, bool]:
        """
        批量检查子编码是否存在
        
        Args:
            item_codes: 子编码列表
            
        Returns:
            {子编码: 是否存在}
        """
        valid_codes = self._load_item_codes()
        
        result = {}
        for code in item_codes:
            if code:
                result[code] = code.strip() in valid_codes
            else:
                result[code] = False
        
        return result
    
    def get_missing_item_codes(self, item_codes: List[str]) -> List[str]:
        """
        获取不存在的子编码列表
        
        Args:
            item_codes: 子编码列表
            
        Returns:
            不存在的子编码列表
        """
        valid_codes = self._load_item_codes()
        
        missing = []
        for code in item_codes:
            if code and code.strip() not in valid_codes:
                missing.append(code)
        
        return missing
    
    def check_parent_code_exists(self, parent_code: str) -> bool:
        """
        检查父编码是否存在于cpcitem表的ITEMCODE字段
        
        Args:
            parent_code: 父编码
            
        Returns:
            是否存在
        """
        # 父编码也是物料编码，使用相同的表
        return self.check_item_code_exists(parent_code)
    
    def check_item_disabled_or_discontinued(self, item_code: str) -> Optional[bool]:
        """
        检查子编码对应的物料是否禁用或停产（ITEMNAME包含"禁用"或"停产"）
        
        Args:
            item_code: 子编码/物料编码
            
        Returns:
            True: 物料禁用或停产，不可用
            False: 物料正常，可用
            None: 物料不存在，无法判断
        """
        item_info = self.get_item_info(item_code)
        if not item_info:
            return None
        
        item_name = item_info.get('item_name') or ''
        if not isinstance(item_name, str):
            item_name = str(item_name)
        
        if '禁用' in item_name or '停产' in item_name:
            return True
        return False
    
    def get_item_info(self, item_code: str) -> Optional[Dict]:
        """
        获取物料详细信息
        
        Args:
            item_code: 物料编码
            
        Returns:
            物料信息字典
        """
        try:
            query = """
                SELECT 
                    ITEMCODE,
                    ITEMNAME,
                    SPEC,
                    ITEMUNIT,
                    STAT
                FROM cpcitem 
                WHERE ITEMCODE = :item_code
            """
            
            engine = self.db_helper.get_engine(self.db_name)
            with engine.connect() as conn:
                result = conn.execute(text(query), {"item_code": item_code})
                row = result.fetchone()
                
                if row:
                    return {
                        'item_code': row[0],
                        'item_name': row[1],
                        'specification': row[2],
                        'unit': row[3],
                        'status': row[4]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"获取物料信息失败 {item_code}: {str(e)}")
            return None
    
    def clear_cache(self):
        """清除缓存"""
        self._item_code_cache = None
        self._parent_code_cache = None
        logger.info("缓存已清除")
    
    def refresh_cache(self):
        """刷新缓存"""
        self.clear_cache()
        self._load_item_codes()
        logger.info("缓存已刷新")


# 全局实例（单例模式）
_db_validator_instance: Optional[DBValidator] = None


def get_db_validator(db_name: str = "plm_sync") -> DBValidator:
    """
    获取数据库验证器实例（单例）
    
    Args:
        db_name: 数据库配置名称
        
    Returns:
        DBValidator实例
    """
    global _db_validator_instance
    
    if _db_validator_instance is None:
        _db_validator_instance = DBValidator(db_name)
    
    return _db_validator_instance
