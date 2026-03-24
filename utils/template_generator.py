#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BOM Excel模板生成器
"""

import pandas as pd
from pathlib import Path


class BOMTemplateGenerator:
    """BOM模板生成器"""
    
    def __init__(self):
        self.template_columns = [
            '父编码',
            'bomviewaltsuid',
            '子编码',
            '用量',
            '位置号',
            '备注',
            '单别（BOM清单|BM11,配电BOM|PBOM,新能源BOM|XBOM,易立高BOM|YBOM）',
            '工单类别（填数字右边是对应值）',
            '单位'
        ]
        
        self.sample_data = [
            {
                '父编码': 'MSF-000163-00',
                'bomviewaltsuid': '0',
                '子编码': 'WIR-001952-00',
                '用量': 1,
                '位置号': '',
                '备注': '',
                '单别（BOM清单|BM11,配电BOM|PBOM,新能源BOM|XBOM,易立高BOM|YBOM）': 'BOM清单|EM11',
                '工单类别（填数字右边是对应值）': '5101',
                '单位': '个'
            },
            {
                '父编码': 'MSF-000163-00',
                'bomviewaltsuid': '0',
                '子编码': 'WIR-001953-00',
                '用量': 1,
                '位置号': '',
                '备注': '',
                '单别（BOM清单|BM11,配电BOM|PBOM,新能源BOM|XBOM,易立高BOM|YBOM）': 'BOM清单|EM11',
                '工单类别（填数字右边是对应值）': '5101',
                '单位': 'kg'
            }
        ]
    
    def generate_empty_template(self, output_path: str) -> str:
        """生成空白模板"""
        df = pd.DataFrame(columns=self.template_columns)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='BOM数据', index=False)
            
            # 字段说明
            desc_df = pd.DataFrame([
                {'字段名': '父编码', '必填': '是', '说明': '父物料编码'},
                {'字段名': 'bomviewaltsuid', '必填': '是', '说明': 'BOM视图替代UID'},
                {'字段名': '子编码', '必填': '是', '说明': '子物料编码'},
                {'字段名': '用量', '必填': '是', '说明': '物料用量（数字）'},
                {'字段名': '位置号', '必填': '否', '说明': '装配位置号'},
                {'字段名': '备注', '必填': '否', '说明': '备注信息'},
                {'字段名': '单别', '必填': '是', '说明': 'BOM清单|EM11等'},
                {'字段名': '工单类别', '必填': '是', '说明': '填数字'},
                {'字段名': '单位', '必填': '是', '说明': '计量单位'}
            ])
            desc_df.to_excel(writer, sheet_name='字段说明', index=False)
        
        return str(output_file)
    
    def generate_sample_template(self, output_path: str) -> str:
        """生成示例模板"""
        df = pd.DataFrame(self.sample_data)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='BOM数据', index=False)
            
            # 字段说明
            desc_df = pd.DataFrame([
                {'字段名': '父编码', '必填': '是', '说明': '父物料编码', '示例': 'MSF-000163-00'},
                {'字段名': 'bomviewaltsuid', '必填': '是', '说明': 'BOM视图替代UID', '示例': '0'},
                {'字段名': '子编码', '必填': '是', '说明': '子物料编码', '示例': 'WIR-001952-00'},
                {'字段名': '用量', '必填': '是', '说明': '物料用量', '示例': '1'},
                {'字段名': '位置号', '必填': '否', '说明': '装配位置号', '示例': 'A1'},
                {'字段名': '备注', '必填': '否', '说明': '备注信息', '示例': ''},
                {'字段名': '单别', '必填': '是', '说明': 'BOM类型', '示例': 'BOM清单|EM11'},
                {'字段名': '工单类别', '必填': '是', '说明': '工单类别', '示例': '5101'},
                {'字段名': '单位', '必填': '是', '说明': '计量单位', '示例': '个'}
            ])
            desc_df.to_excel(writer, sheet_name='字段说明', index=False)
        
        return str(output_file)
