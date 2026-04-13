from typing import Dict, List, Any, Optional
from sqlalchemy import text
from utils.db_helper import DatabaseHelper
from utils.logger import get_default_logger

logger = get_default_logger()


class PLMDataChecker:
    """PLM数据检查器"""
    
    def __init__(self):
        self.db_helper = DatabaseHelper()
        self.cache = {}
    
    def load_plm_data(self) -> Dict[str, Any]:
        """从PLM同步库加载数据"""
        logger.info("开始加载PLM数据...")
        
        plm_data = {
            'materials': self._load_materials(),
            'suppliers': self._load_suppliers(),
            'units': self._load_units(),
        }
        
        logger.info(f"PLM数据加载完成:")
        logger.info(f"  - 物料: {len(plm_data['materials'])} 条")
        logger.info(f"  - 供应商: {len(plm_data['suppliers'])} 条")
        logger.info(f"  - 单位: {len(plm_data['units'])} 条")
        
        return plm_data
    
    def _load_materials(self) -> Dict[str, Dict]:
        """加载物料数据"""
        try:
            session = self.db_helper.get_session('plm_sync')
            # 从CPCITEM表加载物料数据
            query = text("""
                SELECT 
                    itemcode as material_code,
                    itemname as material_name,
                    spec as specification,
                    itemtype as category,
                    itemunit as unit,
                    stat as status,
                    '' as supplier_code,
                    '' as version
                FROM cpcitem
                WHERE stat IS NOT NULL
            """)
            
            result = session.execute(query)
            rows = result.fetchall()
            session.close()
            
            materials = {}
            for row in rows:
                materials[row[0]] = {
                    'material_code': row[0],
                    'material_name': row[1],
                    'specification': row[2],
                    'category': row[3],
                    'unit': row[4],
                    'status': row[5],
                    'supplier_code': row[6],
                    'version': row[7]
                }
            
            return materials
            
        except Exception as e:
            logger.error(f"加载物料数据失败: {str(e)}")
            return {}
    
    def _load_suppliers(self) -> Dict[str, Dict]:
        """加载供应商数据"""
        try:
            session = self.db_helper.get_session('plm_sync')
            # 尝试查询 CPC_VENDOR 表，但由于字段名不确定，暂时返回空字典
            # 供应商数据在当前 BOM 验证规则中不是必需的
            logger.info("跳过供应商数据加载（表结构未知）")
            return {}
            
        except Exception as e:
            logger.warning(f"加载供应商数据失败（表可能不存在或字段名不匹配）: {str(e)}")
            return {}
    
    def _load_units(self) -> Dict[str, Dict]:
        """加载单位数据"""
        try:
            session = self.db_helper.get_session('plm_sync')
            # 从CPCITEM表中提取唯一的单位
            query = text("""
                SELECT DISTINCT
                    itemunit as unit_code,
                    itemunit as unit_name,
                    '' as unit_type,
                    1 as conversion_factor,
                    itemunit as base_unit
                FROM cpcitem
                WHERE itemunit IS NOT NULL AND itemunit != ''
            """)
            
            result = session.execute(query)
            rows = result.fetchall()
            session.close()
            
            units = {}
            for row in rows:
                units[row[0]] = {
                    'unit_code': row[0],
                    'unit_name': row[1],
                    'unit_type': row[2],
                    'conversion_factor': row[3],
                    'base_unit': row[4]
                }
            
            return units
            
        except Exception as e:
            logger.error(f"加载单位数据失败: {str(e)}")
            return {}
    
    def get_material_info(self, material_code: str) -> Optional[Dict]:
        """获取物料信息"""
        if 'materials' not in self.cache:
            self.cache['materials'] = self._load_materials()
        
        return self.cache['materials'].get(material_code)
    
    def get_supplier_info(self, supplier_code: str) -> Optional[Dict]:
        """获取供应商信息"""
        if 'suppliers' not in self.cache:
            self.cache['suppliers'] = self._load_suppliers()
        
        return self.cache['suppliers'].get(supplier_code)
    
    def is_valid_unit(self, unit_code: str) -> bool:
        """检查单位是否有效"""
        if 'units' not in self.cache:
            self.cache['units'] = self._load_units()
        
        return unit_code in self.cache['units']
    
    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()
        logger.info("PLM数据缓存已清除")
