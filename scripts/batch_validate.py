#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量校验BOM文件
用于批量处理多个BOM文件
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from validator.validation_engine import ValidationEngine
from report.html_generator import HTMLReportGenerator
from report.excel_generator import ExcelReportGenerator
from utils.logger import get_default_logger

logger = get_default_logger()


def batch_validate(input_dir: str, output_dir: str = None, pattern: str = "*.xlsx"):
    """批量校验BOM文件"""
    
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        return
    
    if not input_path.is_dir():
        logger.error(f"输入路径不是目录: {input_dir}")
        return
    
    output_path = Path(output_dir) if output_dir else Path('reports/batch')
    output_path.mkdir(parents=True, exist_ok=True)
    
    bom_files = list(input_path.glob(pattern))
    
    if not bom_files:
        logger.warning(f"未找到匹配的文件: {pattern}")
        return
    
    logger.info(f"找到 {len(bom_files)} 个BOM文件")
    
    validation_engine = ValidationEngine()
    html_generator = HTMLReportGenerator()
    excel_generator = ExcelReportGenerator()
    
    results_summary = []
    
    for i, bom_file in enumerate(bom_files, 1):
        print(f"\n[{i}/{len(bom_files)}] 校验: {bom_file.name}")
        print("-" * 60)
        
        try:
            result = validation_engine.validate_bom_file(str(bom_file))
            
            report_name = f"{bom_file.stem}_report"
            
            html_path = output_path / f"{report_name}.html"
            html_generator.generate(result, str(html_path))
            
            excel_path = output_path / f"{report_name}.xlsx"
            excel_generator.generate(result, str(excel_path))
            
            print(f"  总行数: {result.total_rows}")
            print(f"  有效行数: {result.valid_rows}")
            print(f"  错误数: {result.error_count}")
            print(f"  警告数: {result.warning_count}")
            print(f"  通过率: {result.pass_rate:.2f}%")
            print(f"  结果: {'✓ 通过' if result.is_valid else '✗ 失败'}")
            print(f"  报告: {html_path}")
            
            results_summary.append({
                '文件名': bom_file.name,
                '总行数': result.total_rows,
                '有效行数': result.valid_rows,
                '错误数': result.error_count,
                '警告数': result.warning_count,
                '通过率': f"{result.pass_rate:.2f}%",
                '结果': '通过' if result.is_valid else '失败',
                'HTML报告': str(html_path),
                'Excel报告': str(excel_path)
            })
            
        except Exception as e:
            logger.error(f"校验失败 {bom_file.name}: {str(e)}")
            results_summary.append({
                '文件名': bom_file.name,
                '总行数': 0,
                '有效行数': 0,
                '错误数': 0,
                '警告数': 0,
                '通过率': '0%',
                '结果': '异常',
                'HTML报告': '',
                'Excel报告': '',
                '错误信息': str(e)
            })
    
    summary_file = output_path / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df = pd.DataFrame(results_summary)
    df.to_excel(summary_file, index=False)
    
    print("\n" + "="*80)
    print("批量校验完成")
    print("="*80)
    print(f"总文件数: {len(bom_files)}")
    print(f"通过数: {sum(1 for r in results_summary if r['结果'] == '通过')}")
    print(f"失败数: {sum(1 for r in results_summary if r['结果'] == '失败')}")
    print(f"异常数: {sum(1 for r in results_summary if r['结果'] == '异常')}")
    print(f"\n汇总报告: {summary_file}")
    print("="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量校验BOM文件')
    parser.add_argument(
        '--input',
        '-i',
        required=True,
        help='BOM文件所在目录'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='报告输出目录（默认: reports/batch）'
    )
    parser.add_argument(
        '--pattern',
        '-p',
        default='*.xlsx',
        help='文件匹配模式（默认: *.xlsx）'
    )
    
    args = parser.parse_args()
    
    load_dotenv()
    
    logger.info("="*60)
    logger.info("批量BOM校验程序启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        batch_validate(args.input, args.output, args.pattern)
        return 0
    except Exception as e:
        logger.error(f"批量校验异常: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
