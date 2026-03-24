#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
校验Excel文件中的所有Sheet
适用于一个Excel文件包含多个BOM清单的情况
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from validator.validation_engine import ValidationEngine
from validator.bom_reader import BOMReader
from report.html_generator import HTMLReportGenerator
from report.excel_generator import ExcelReportGenerator
from utils.logger import get_default_logger

logger = get_default_logger()


def validate_all_sheets(file_path: str, output_dir: str = None):
    """校验Excel文件中的所有Sheet"""
    
    file = Path(file_path)
    if not file.exists():
        logger.error(f"文件不存在: {file_path}")
        return
    
    output_path = Path(output_dir) if output_dir else Path('reports/multi_sheet')
    output_path.mkdir(parents=True, exist_ok=True)
    
    reader = BOMReader()
    sheet_names = reader.get_sheet_names(file_path)
    
    if not sheet_names:
        logger.error("无法读取Sheet列表")
        return
    
    logger.info(f"找到 {len(sheet_names)} 个Sheet: {', '.join(sheet_names)}")
    
    validation_engine = ValidationEngine()
    html_generator = HTMLReportGenerator()
    excel_generator = ExcelReportGenerator()
    
    all_results = []
    
    print("\n" + "="*80)
    print(f"开始校验文件: {file.name}")
    print("="*80)
    
    for i, sheet_name in enumerate(sheet_names, 1):
        print(f"\n[{i}/{len(sheet_names)}] 校验Sheet: {sheet_name}")
        print("-" * 60)
        
        try:
            result = validation_engine.validate_bom_file(file_path, sheet_name)
            
            report_name = f"{file.stem}_{sheet_name}_report"
            safe_report_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in report_name)
            
            html_path = output_path / f"{safe_report_name}.html"
            html_generator.generate(result, str(html_path))
            
            excel_path = output_path / f"{safe_report_name}.xlsx"
            excel_generator.generate(result, str(excel_path))
            
            print(f"  总行数: {result.total_rows}")
            print(f"  有效行数: {result.valid_rows}")
            print(f"  错误数: {result.error_count}")
            print(f"  警告数: {result.warning_count}")
            print(f"  通过率: {result.pass_rate:.2f}%")
            print(f"  结果: {'✓ 通过' if result.is_valid else '✗ 失败'}")
            
            all_results.append({
                'sheet_name': sheet_name,
                'result': result,
                'html_report': html_path,
                'excel_report': excel_path
            })
            
        except Exception as e:
            logger.error(f"校验Sheet失败 {sheet_name}: {str(e)}")
            all_results.append({
                'sheet_name': sheet_name,
                'result': None,
                'error': str(e)
            })
    
    print("\n" + "="*80)
    print("所有Sheet校验完成")
    print("="*80)
    
    total_sheets = len(all_results)
    passed_sheets = sum(1 for r in all_results if r.get('result') and r['result'].is_valid)
    failed_sheets = sum(1 for r in all_results if r.get('result') and not r['result'].is_valid)
    error_sheets = sum(1 for r in all_results if not r.get('result'))
    
    print(f"总Sheet数: {total_sheets}")
    print(f"通过: {passed_sheets}")
    print(f"失败: {failed_sheets}")
    print(f"异常: {error_sheets}")
    
    print("\n详细结果:")
    for r in all_results:
        sheet_name = r['sheet_name']
        if r.get('result'):
            result = r['result']
            status = '✓ 通过' if result.is_valid else '✗ 失败'
            print(f"  [{status}] {sheet_name}: {result.error_count}错误, {result.warning_count}警告")
        else:
            print(f"  [✗ 异常] {sheet_name}: {r.get('error', '未知错误')}")
    
    print("\n报告目录:", output_path)
    print("="*80)
    
    return all_results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='校验Excel文件的所有Sheet')
    parser.add_argument(
        '--input',
        '-i',
        required=True,
        help='Excel文件路径'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='报告输出目录（默认: reports/multi_sheet）'
    )
    
    args = parser.parse_args()
    
    load_dotenv()
    
    logger.info("="*60)
    logger.info("多Sheet BOM校验程序启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        validate_all_sheets(args.input, args.output)
        return 0
    except Exception as e:
        logger.error(f"程序执行异常: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
