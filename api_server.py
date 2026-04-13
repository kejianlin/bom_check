#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BOM校验Web API服务
提供HTTP接口供其他系统集成
"""

from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

from validator.validation_engine import ValidationEngine
from report.html_generator import HTMLReportGenerator
from report.excel_generator import ExcelReportGenerator
from report.excel_markup_generator import ExcelMarkupGenerator, ExcelErrorReportGenerator
from scripts.generate_bom_template import create_bom_template
from utils.logger import get_default_logger
from validator.excel_runtime import get_excel_reader_mode, supports_markup_report
from validator.file_guard import ExcelFileGuardError

app = Flask(__name__, template_folder='templates')
CORS(app)

logger = get_default_logger()

UPLOAD_FOLDER = Path('temp/uploads')
REPORT_FOLDER = Path('reports')
TEMPLATE_FOLDER = Path('templates/generated')
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)
TEMPLATE_FOLDER.mkdir(parents=True, exist_ok=True)

# 使用新的配置文件
validation_engine = ValidationEngine(config_path='config/validation_rules.yaml')


def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """首页重定向到上传页面"""
    return render_template('upload.html')


@app.route('/upload')
def upload_page():
    """上传页面"""
    return render_template('upload.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'BOM Validation API',
        'excel_reader_mode': get_excel_reader_mode()
    })


@app.route('/api/template/empty', methods=['GET'])
def download_empty_template():
    """下载空白模板"""
    try:
        template_path = TEMPLATE_FOLDER / 'bom_template_empty.xlsx'
        
        # 如果模板不存在或需要重新生成，使用新的生成器
        if not template_path.exists():
            logger.info(f"生成空白模板: {template_path}")
            # 生成50行空白模板
            create_bom_template(output_path=str(template_path), num_rows=50)
        
        return send_file(
            str(template_path),
            as_attachment=True,
            download_name='BOM空白模板.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"下载空白模板失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/template/sample', methods=['GET'])
def download_sample_template():
    """下载示例模板（包含示例数据）"""
    try:
        template_path = TEMPLATE_FOLDER / 'bom_template_sample.xlsx'
        
        # 如果模板不存在或需要重新生成，使用新的生成器
        if not template_path.exists():
            logger.info(f"生成示例模板: {template_path}")
            # 生成30行模板（第一行是示例数据）
            create_bom_template(output_path=str(template_path), num_rows=30)
        
        return send_file(
            str(template_path),
            as_attachment=True,
            download_name='BOM示例模板.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"下载示例模板失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/template/custom', methods=['GET'])
def download_custom_template():
    """下载自定义行数的模板"""
    try:
        # 获取行数参数，默认20行
        num_rows = int(request.args.get('rows', 20))
        
        # 限制行数范围
        if num_rows < 1:
            num_rows = 1
        elif num_rows > 1000:
            num_rows = 1000
        
        # 生成临时文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        template_filename = f'bom_template_{num_rows}rows_{timestamp}.xlsx'
        template_path = TEMPLATE_FOLDER / template_filename
        
        logger.info(f"生成自定义模板: {num_rows}行")
        create_bom_template(output_path=str(template_path), num_rows=num_rows)
        
        return send_file(
            str(template_path),
            as_attachment=True,
            download_name=f'BOM模板_{num_rows}行.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"下载自定义模板失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate', methods=['POST'])
def validate_bom():
    """
    校验BOM文件
    
    请求参数:
    - bom_file: Excel文件（multipart/form-data）
    - sheet_name: 可选，指定sheet名称
    - format: 可选，报告格式 (html/excel/both)
    
    返回:
    - report_id: 报告ID
    - is_valid: 是否通过校验
    - error_count: 错误数量
    - warning_count: 警告数量
    - pass_rate: 通过率
    - report_urls: 包含以下链接：
        - html: HTML验证报告
        - excel: Excel汇总报告
        - marked: 标注版Excel文件（原文件 + 错误标记）
        - error_detail: 详细错误列表Excel文件
    """
    try:
        logger.info("收到校验请求")
        logger.info(f"ValidationEngine配置: {validation_engine.config_path}")
        logger.info(f"BOMReader必填列: {validation_engine.bom_reader.required_columns}")
        
        if 'bom_file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['bom_file']
        
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式，仅支持.xlsx和.xls'}), 400
        
        filename = secure_filename(file.filename)
        report_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        upload_path = UPLOAD_FOLDER / f"{report_id}_{filename}"
        file.save(str(upload_path))
        
        logger.info(f"接收到BOM文件: {filename}, 报告ID: {report_id}")
        logger.info(f"文件保存路径: {upload_path}")
        
        sheet_name = request.form.get('sheet_name')
        report_format = request.form.get('format', 'both').lower().split(',')
        
        logger.info(f"Excel读取模式: {get_excel_reader_mode()}")
        if not supports_markup_report():
            logger.info("当前模式下将跳过原文件标注报告，回退为汇总报告")

        logger.info(f"开始校验文件: {upload_path}")
        result = validation_engine.validate_bom_file(str(upload_path), sheet_name)
        logger.info(f"校验完成: 总行数={result.total_rows}, 错误数={result.error_count}")
        
        report_paths = {}
        
        # 生成HTML/Excel汇总报告
        if 'html' in report_format or 'both' in report_format:
            html_path = REPORT_FOLDER / f"{report_id}.html"
            html_generator = HTMLReportGenerator()
            html_generator.generate(result, str(html_path))
            report_paths['html'] = f"/api/report/{report_id}.html"
        
        if 'excel' in report_format or 'both' in report_format:
            excel_path = REPORT_FOLDER / f"{report_id}.xlsx"
            excel_generator = ExcelReportGenerator()
            excel_generator.generate(result, str(excel_path))
            report_paths['excel_summary'] = f"/api/report/{report_id}.xlsx"
        
        # 生成标注后的原文件（带错误标记）
        if supports_markup_report():
            try:
                markup_path = REPORT_FOLDER / f"{report_id}_marked.xlsx"
                markup_generator = ExcelMarkupGenerator()
                # 直接在复制版本上标注：原文件自动拷贝到marked输出路径
                markup_generator.generate(result, str(upload_path), str(markup_path))
                report_paths['marked'] = f"/api/report/{report_id}_marked.xlsx"
                logger.info(f"已生成标注文件: {markup_path}")

                # 默认指向标注版（代替传统Excel汇总）
                report_paths['excel'] = report_paths['marked']
            except Exception as e:
                logger.error(f"生成标注文件失败: {str(e)}")
                # 如果标注失败而用户请求excel，则回退到汇总报告（如已产生）
                if 'excel_summary' in report_paths:
                    report_paths['excel'] = report_paths['excel_summary']
        elif 'excel_summary' in report_paths:
            report_paths['excel'] = report_paths['excel_summary']
        
        # 生成详细错误报告
        try:
            error_report_path = REPORT_FOLDER / f"{report_id}_errors.xlsx"
            error_report_generator = ExcelErrorReportGenerator()
            error_report_generator.generate(result, str(error_report_path))
            report_paths['error_detail'] = f"/api/report/{report_id}_errors.xlsx"
            logger.info(f"已生成错误详情报告: {error_report_path}")
        except Exception as e:
            logger.error(f"生成错误详情报告失败: {str(e)}")
        
        response = {
            'report_id': report_id,
            'file_name': filename,
            'validation_time': result.validation_time.isoformat(),
            'is_valid': result.is_valid,
            'total_rows': result.total_rows,
            'valid_rows': result.valid_rows,
            'error_count': result.error_count,
            'warning_count': result.warning_count,
            'pass_rate': round(result.pass_rate, 2),
            'report_urls': report_paths,
            'error_summary': result.get_error_summary(),
            'warning_summary': result.get_warning_summary()
        }
        
        logger.info(f"校验完成: {filename}, 结果: {'通过' if result.is_valid else '失败'}")
        
        return jsonify(response), 200
        
    except (ValueError, ExcelFileGuardError) as e:
        logger.warning(f"校验请求被拒绝: {str(e)}")
        return jsonify({'error': str(e)}), 400

    except Exception as e:
        logger.error(f"校验处理失败: {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/<filename>', methods=['GET'])
def get_report(filename):
    """
    下载校验报告
    
    参数:
    - filename: 报告文件名（包含扩展名）
    """
    try:
        report_path = REPORT_FOLDER / filename
        
        if not report_path.exists():
            return jsonify({'error': '报告不存在'}), 404
        
        return send_file(
            str(report_path),
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载报告失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync/status', methods=['GET'])
def sync_status():
    """
    获取数据同步状态
    """
    try:
        from sync.sync_engine import SyncEngine
        sync_engine = SyncEngine()
        
        days = int(request.args.get('days', 7))
        stats = sync_engine.get_sync_statistics(days)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"获取同步状态失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync/trigger', methods=['POST'])
def trigger_sync():
    """
    手动触发数据同步
    
    请求参数:
    - mode: 同步模式 (full/incremental)
    - tables: 可选，要同步的表列表
    """
    try:
        from sync.sync_engine import SyncEngine
        
        data = request.get_json() or {}
        mode = data.get('mode', 'incremental')
        tables = data.get('tables')
        
        sync_engine = SyncEngine()
        
        if tables:
            results = {}
            for table in tables:
                result = sync_engine.sync_table(table, mode)
                results[table] = result
        else:
            results = sync_engine.sync_all_tables(mode)
        
        return jsonify({
            'status': 'success',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"触发同步失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules', methods=['GET'])
def get_validation_rules():
    """获取当前的校验规则配置"""
    try:
        import yaml
        with open('config/validation_rules.yaml', 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        
        return jsonify(rules), 200
        
    except Exception as e:
        logger.error(f"获取校验规则失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    import os
    from utils.env_loader import load_project_env
    
    dotenv_path = load_project_env()
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"启动BOM校验API服务: http://{host}:{port}")
    logger.info(f"Excel读取模式: {get_excel_reader_mode()}")
    logger.info(f"环境变量文件: {dotenv_path}")
    logger.info("API文档:")
    logger.info("  POST /api/validate - 校验BOM文件")
    logger.info("  GET  /api/report/<filename> - 下载报告")
    logger.info("  GET  /api/template/empty - 下载空白模板")
    logger.info("  GET  /api/template/sample - 下载示例模板")
    logger.info("  GET  /api/template/custom?rows=N - 下载自定义行数模板")
    logger.info("  GET  /api/sync/status - 获取同步状态")
    logger.info("  POST /api/sync/trigger - 手动触发同步")
    logger.info("  GET  /api/rules - 获取校验规则")
    
    app.run(host=host, port=port, debug=debug)
