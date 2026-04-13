#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BOM自动化校验主程序（命令行校验）
用于校验Excel BOM文件并生成校验报告
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

from validator.validation_engine import ValidationEngine
from report.html_generator import HTMLReportGenerator
from report.excel_generator import ExcelReportGenerator
from utils.logger import get_default_logger
from utils.env_loader import load_project_env

logger = get_default_logger()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BOM自动化校验工具')
    parser.add_argument(
        '--input',
        '-i',
        required=True,
        help='BOM Excel文件路径'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='报告输出路径（不指定则自动生成）'
    )
    parser.add_argument(
        '--sheet',
        '-s',
        help='指定要校验的sheet名称'
    )
    parser.add_argument(
        '--format',
        '-f',
        choices=['html', 'excel', 'both'],
        default='both',
        help='报告格式: html, excel, both（默认）'
    )
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='只执行校验，不生成报告'
    )
    
    args = parser.parse_args()
    
    dotenv_path = load_project_env()
    
    logger.info("="*60)
    logger.info("BOM自动化校验程序启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"环境变量文件: {dotenv_path}")
    logger.info("="*60)
    
    try:
        input_file = Path(args.input)
        if not input_file.exists():
            logger.error(f"输入文件不存在: {args.input}")
            return 1
        
        validation_engine = ValidationEngine()
        
        logger.info(f"开始校验文件: {input_file.name}")
        result = validation_engine.validate_bom_file(str(input_file), args.sheet)
        
        print("\n" + "="*80)
        print("校验结果摘要")
        print("="*80)
        print(f"文件名: {result.file_name}")
        print(f"总行数: {result.total_rows}")
        print(f"有效行数: {result.valid_rows}")
        print(f"错误数: {result.error_count}")
        print(f"警告数: {result.warning_count}")
        print(f"通过率: {result.pass_rate:.2f}%")
        print(f"校验结果: {'✓ 通过' if result.is_valid else '✗ 失败'}")
        print("="*80)
        
        if result.error_count > 0:
            print("\n错误分类统计:")
            for rule_name, count in result.get_error_summary().items():
                print(f"  - {rule_name}: {count} 个")
        
        if result.warning_count > 0:
            print("\n警告分类统计:")
            for rule_name, count in result.get_warning_summary().items():
                print(f"  - {rule_name}: {count} 个")
        
        if not args.no_report:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = input_file.stem
            
            if args.output:
                output_base = Path(args.output).stem
                output_dir = Path(args.output).parent
            else:
                output_base = f"{base_name}_report_{timestamp}"
                output_dir = Path('reports')
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if args.format in ['html', 'both']:
                html_path = output_dir / f"{output_base}.html"
                html_generator = HTMLReportGenerator()
                html_generator.generate(result, str(html_path))
                print(f"\nHTML报告已生成: {html_path}")
            
            if args.format in ['excel', 'both']:
                excel_path = output_dir / f"{output_base}.xlsx"
                excel_generator = ExcelReportGenerator()
                excel_generator.generate(result, str(excel_path))
                print(f"Excel报告已生成: {excel_path}")
        
        if result.is_valid:
            logger.info("校验通过，BOM文件符合要求")
            return 0
        else:
            logger.warning("校验失败，请查看报告了解详情")
            return 1
        
    except Exception as e:
        logger.error(f"程序执行异常: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
