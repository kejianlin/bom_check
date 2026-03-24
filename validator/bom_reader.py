import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from models.bom_models import BOMItem
from utils.logger import get_default_logger

logger = get_default_logger()


def _coerce_value_to_str(value):
    """将原始值标准化为字符串，去掉浮点末尾.0"""
    if pd.isna(value):
        return None

    if isinstance(value, (int,)):
        return str(value)

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).rstrip('0').rstrip('.')

    try:
        text = str(value).strip()
        if text.endswith('.0') and text.replace('.0', '', 1).isdigit():
            return text[:-2]
        return text
    except Exception:
        return None


class BOMReader:
    """BOM Excel文件读取器"""
    
    def __init__(self, required_columns: List[str] = None):
        self.required_columns = required_columns or [
            'parent_code',
            'bomviewaltsuid',
            'child_code',
            'quantity',
            'order_type',
            'work_order_category',
            'unit'
        ]
    
    def read_excel(self, file_path: str, sheet_name: str = None) -> List[BOMItem]:
        """读取Excel文件"""
        logger.info(f"开始读取BOM文件: {file_path}")
        
        file = Path(file_path)
        if not file.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if file.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"不支持的文件格式: {file.suffix}")
        
        try:
            # 如果没有指定sheet，尝试自动选择合适的sheet
            if not sheet_name:
                sheet_name = self._find_best_sheet(file_path)
                if sheet_name:
                    logger.info(f"自动选择sheet: {sheet_name}")
            
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
            
            logger.info(f"成功读取 {len(df)} 行数据")
            logger.info(f"原始列名: {list(df.columns)}")
            
            # 清理完全空的行
            df = df.dropna(how='all')
            
            # 清理列名为空的列
            df = df.loc[:, df.columns.notna()]
            
            logger.info(f"清理空行后剩余 {len(df)} 行数据")
            
            df = self._normalize_columns(df)
            
            logger.info(f"标准化后的列名: {list(df.columns)}")
            logger.info(f"必填列: {self.required_columns}")
            
            missing_columns = self._check_required_columns(df)
            if missing_columns:
                logger.error(f"缺少必需列: {missing_columns}")
                logger.error(f"当前列: {list(df.columns)}")
                
                # 生成更友好的错误提示
                error_msg = f"缺少必需列: {', '.join(missing_columns)}\n"
                error_msg += f"当前Excel列: {list(df.columns)}\n"
                error_msg += "\n可能的原因:\n"
                error_msg += "1. Excel文件格式不正确（应该是横向表格，不是竖向的项目-值格式）\n"
                error_msg += "2. 读取了错误的sheet\n"
                error_msg += "3. 列名不匹配\n"
                error_msg += "\n请确保Excel包含以下列（中文或英文）:\n"
                error_msg += "  - 父编码 (parent_code)\n"
                error_msg += "  - bomviewaltsuid\n"
                error_msg += "  - 子编码 (child_code)\n"
                error_msg += "  - 用量 (quantity)\n"
                error_msg += "  - 单别 (order_type)\n"
                error_msg += "  - 工单类别 (work_order_category)\n"
                error_msg += "  - 单位 (unit)\n"
                error_msg += "\n建议: 使用模板文件或运行 python 检查excel文件.py <文件路径> 检查文件结构"
                
                raise ValueError(error_msg)
            
            bom_items = self._convert_to_bom_items(df)
            
            logger.info(f"成功解析 {len(bom_items)} 个BOM条目")
            return bom_items
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            raise
    
    def _find_best_sheet(self, file_path: str) -> str:
        """自动查找最合适的BOM数据sheet"""
        try:
            excel_file = pd.ExcelFile(file_path)
            
            # 如果只有一个sheet，直接返回
            if len(excel_file.sheet_names) == 1:
                return None  # 使用默认
            
            logger.info(f"Excel包含多个sheet: {excel_file.sheet_names}")
            
            # 评分系统：找到最可能包含BOM数据的sheet
            best_sheet = None
            best_score = 0
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                    score = 0
                    
                    # 跳过空sheet
                    if len(df) == 0 or len(df.columns) < 3:
                        continue
                    
                    # 跳过竖向格式（项目-值格式）
                    if len(df.columns) == 2 and str(df.columns[0]) in ['项目', '字段', 'Field', 'Name']:
                        logger.info(f"跳过竖向格式sheet: {sheet_name}")
                        continue
                    
                    # 检查是否包含BOM相关的列名
                    bom_keywords = ['父编码', '子编码', 'parent', 'child', 'bom', 'material', 
                                   'code', '编码', '物料', '用量', 'quantity', 'bomviewaltsuid']
                    
                    for col in df.columns:
                        col_str = str(col).lower()
                        for keyword in bom_keywords:
                            if keyword.lower() in col_str:
                                score += 1
                                break
                    
                    # 列数越多，越可能是BOM数据
                    score += len(df.columns) * 0.1
                    
                    # 行数合理（不要太少也不要太多）
                    if 2 <= len(df) <= 10000:
                        score += 1
                    
                    logger.info(f"Sheet '{sheet_name}': 列数={len(df.columns)}, 行数={len(df)}, 得分={score:.1f}")
                    
                    if score > best_score:
                        best_score = score
                        best_sheet = sheet_name
                        
                except Exception as e:
                    logger.warning(f"读取sheet '{sheet_name}' 失败: {str(e)}")
                    continue
            
            if best_sheet:
                logger.info(f"选择最佳sheet: {best_sheet} (得分: {best_score:.1f})")
            
            return best_sheet
            
        except Exception as e:
            logger.warning(f"自动选择sheet失败: {str(e)}")
            return None
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            '父编码': 'parent_code',
            '父物料编码': 'parent_code',
            '母件编码': 'parent_code',
            'bomviewaltsuid': 'bomviewaltsuid',
            'BOMVIEWALTSUID': 'bomviewaltsuid',
            '子编码': 'child_code',
            '子编码ITRMCODE': 'child_code',
            'ITRMCODE': 'child_code',
            '子物料编码': 'child_code',
            '物料编码': 'child_code',
            '物料代码': 'child_code',
            '料号': 'child_code',
            '物料名称': 'material_name',
            '品名': 'material_name',
            '名称': 'material_name',
            '用量': 'quantity',
            '数量': 'quantity',
            '位置号': 'position_number',
            '单别': 'order_type',
            '单别（BOM清单|BM11,配电BOM|PBOM,新能源BOM|XBOM,易立高BOM|YBOM）': 'order_type',
            '工单类别': 'work_order_category',
            '工单类别（填数字右边是对应值）': 'work_order_category',
            '单位': 'unit',
            '计量单位': 'unit',
            '规格': 'specification',
            '规格型号': 'specification',
            '型号': 'specification',
            '供应商': 'supplier',
            '供应商名称': 'supplier',
            '备注': 'remark',
            '说明': 'remark',
            '版本': 'version',
            '替代料': 'substitute',
        }
        
        new_columns = []
        for col in df.columns:
            col_str = str(col).strip()
            normalized = column_mapping.get(col_str, col_str)
            new_columns.append(normalized)
        
        df.columns = new_columns
        return df
    
    def _check_required_columns(self, df: pd.DataFrame) -> List[str]:
        """检查必需列"""
        missing = []
        for col in self.required_columns:
            if col not in df.columns:
                missing.append(col)
        return missing
    
    def _convert_to_bom_items(self, df: pd.DataFrame) -> List[BOMItem]:
        """转换为BOM条目对象"""
        items = []
        
        for idx, row in df.iterrows():
            row_num = idx + 2
            
            # 过滤空行：检查关键字段是否都为空
            parent_code = str(row.get('parent_code', '')).strip()
            child_code = str(row.get('child_code', '')).strip()
            
            # 如果父编码和子编码都为空，跳过此行
            if not parent_code and not child_code:
                logger.debug(f"跳过空行: 第{row_num}行")
                continue
            
            # 检查是否整行都是NaN或空值
            non_empty_count = sum(1 for v in row.values if pd.notna(v) and str(v).strip() != '')
            if non_empty_count == 0:
                logger.debug(f"跳过全空行: 第{row_num}行")
                continue
            
            item = BOMItem(
                row_number=row_num,
                parent_code=parent_code,
                child_code=child_code,
                material_name=_coerce_value_to_str(row.get('material_name', None)),
                bomviewaltsuid=_coerce_value_to_str(row.get('bomviewaltsuid', None)),
                quantity=self._parse_float(row.get('quantity')),
                position_number=_coerce_value_to_str(row.get('position_number', None)),
                order_type=_coerce_value_to_str(row.get('order_type', None)),
                work_order_category=_coerce_value_to_str(row.get('work_order_category', None)),
                unit=_coerce_value_to_str(row.get('unit', None)),
                specification=_coerce_value_to_str(row.get('specification', None)),
                supplier=_coerce_value_to_str(row.get('supplier', None)),
                remark=_coerce_value_to_str(row.get('remark', None)),
                version=_coerce_value_to_str(row.get('version', None)),
                substitute=_coerce_value_to_str(row.get('substitute', None)),
                raw_data=row.to_dict()
            )
            
            items.append(item)
        
        logger.info(f"过滤空行后剩余 {len(items)} 条有效数据")
        return items
    
    def _parse_float(self, value) -> float:
        """解析浮点数"""
        if pd.isna(value):
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def get_sheet_names(self, file_path: str) -> List[str]:
        """获取Excel文件中的所有sheet名称"""
        try:
            excel_file = pd.ExcelFile(file_path)
            return excel_file.sheet_names
        except Exception as e:
            logger.error(f"获取sheet名称失败: {str(e)}")
            return []
