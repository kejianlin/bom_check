from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from models.bom_models import ValidationResult, ValidationError
from utils.logger import get_default_logger
from jinja2 import Template

logger = get_default_logger()


class HTMLReportGenerator:
    """HTML报告生成器"""
    
    def __init__(self, template_path: str = None):
        self.template_path = template_path or "report/templates/report_template.html"
    
    def generate(self, result: ValidationResult, output_path: str):
        """生成HTML报告"""
        logger.info(f"开始生成HTML报告: {output_path}")
        
        try:
            template_file = Path(self.template_path)
            
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                template_content = self._get_default_template()
            
            template = Template(template_content)
            
            context = self._prepare_context(result)
            
            html_content = template.render(**context)
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML报告生成成功: {output_path}")
            
        except Exception as e:
            logger.error(f"生成HTML报告失败: {str(e)}")
            raise
    
    def _prepare_context(self, result: ValidationResult) -> Dict[str, Any]:
        """准备模板上下文"""
        return {
            'file_name': result.file_name,
            'validation_time': result.validation_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_rows': result.total_rows,
            'valid_rows': result.valid_rows,
            'error_count': result.error_count,
            'warning_count': result.warning_count,
            'pass_rate': f"{result.pass_rate:.2f}",
            'is_valid': result.is_valid,
            'errors': result.errors,
            'warnings': result.warnings,
            'error_summary': result.get_error_summary(),
            'warning_summary': result.get_warning_summary(),
            'items': result.items
        }
    
    def _get_default_template(self) -> str:
        """获取默认HTML模板"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOM校验报告 - {{ file_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #fafafa;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        
        .summary-card .label {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        
        .summary-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }
        
        .summary-card.success .value {
            color: #4caf50;
        }
        
        .summary-card.error .value {
            color: #f44336;
        }
        
        .summary-card.warning .value {
            color: #ff9800;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }
        
        .status-badge.pass {
            background: #4caf50;
            color: white;
        }
        
        .status-badge.fail {
            background: #f44336;
            color: white;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            font-size: 22px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            font-size: 14px;
        }
        
        thead {
            background: #f5f5f5;
        }
        
        th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #ddd;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        
        tbody tr:hover {
            background: #f9f9f9;
        }
        
        .error-row {
            background: #ffebee;
        }
        
        .warning-row {
            background: #fff3e0;
        }
        
        .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .severity-error {
            background: #f44336;
            color: white;
        }
        
        .severity-warning {
            background: #ff9800;
            color: white;
        }
        
        .chart-container {
            margin: 20px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }
        
        .footer {
            background: #fafafa;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }
        
        .no-data {
            padding: 40px;
            text-align: center;
            color: #999;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>BOM自动化校验报告</h1>
            <div class="subtitle">{{ file_name }} | {{ validation_time }}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="label">总行数</div>
                <div class="value">{{ total_rows }}</div>
            </div>
            <div class="summary-card success">
                <div class="label">有效行数</div>
                <div class="value">{{ valid_rows }}</div>
            </div>
            <div class="summary-card error">
                <div class="label">错误数量</div>
                <div class="value">{{ error_count }}</div>
            </div>
            <div class="summary-card warning">
                <div class="label">警告数量</div>
                <div class="value">{{ warning_count }}</div>
            </div>
            <div class="summary-card">
                <div class="label">通过率</div>
                <div class="value">{{ pass_rate }}%</div>
                {% if is_valid %}
                <div class="status-badge pass">✓ 校验通过</div>
                {% else %}
                <div class="status-badge fail">✗ 校验失败</div>
                {% endif %}
            </div>
        </div>
        
        <div class="content">
            {% if error_count > 0 %}
            <div class="section">
                <h2>错误列表 ({{ error_count }})</h2>
                
                <div class="chart-container">
                    <h3>错误分类统计</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>错误类型</th>
                                <th>数量</th>
                                <th>占比</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for rule_name, count in error_summary.items() %}
                            <tr>
                                <td>{{ rule_name }}</td>
                                <td>{{ count }}</td>
                                <td>{{ "%.1f" | format((count / error_count * 100)) }}%</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>行号</th>
                            <th>规则</th>
                            <th>字段</th>
                            <th>错误描述</th>
                            <th>期望值</th>
                            <th>实际值</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for error in errors %}
                        <tr class="error-row">
                            <td>{{ error.row_number }}</td>
                            <td><span class="severity-badge severity-error">ERROR</span> {{ error.rule_name }}</td>
                            <td>{{ error.field }}</td>
                            <td>{{ error.message }}</td>
                            <td>{{ error.expected_value if error.expected_value else '-' }}</td>
                            <td>{{ error.actual_value if error.actual_value else '-' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            {% if warning_count > 0 %}
            <div class="section">
                <h2>警告列表 ({{ warning_count }})</h2>
                
                <table>
                    <thead>
                        <tr>
                            <th>行号</th>
                            <th>规则</th>
                            <th>字段</th>
                            <th>警告描述</th>
                            <th>期望值</th>
                            <th>实际值</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for warning in warnings %}
                        <tr class="warning-row">
                            <td>{{ warning.row_number }}</td>
                            <td><span class="severity-badge severity-warning">WARNING</span> {{ warning.rule_name }}</td>
                            <td>{{ warning.field }}</td>
                            <td>{{ warning.message }}</td>
                            <td>{{ warning.expected_value if warning.expected_value else '-' }}</td>
                            <td>{{ warning.actual_value if warning.actual_value else '-' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            {% if error_count == 0 and warning_count == 0 %}
            <div class="no-data">
                ✓ 恭喜！所有BOM条目均通过校验，无错误和警告。
            </div>
            {% endif %}
            
            <div class="section">
                <h2>建议措施</h2>
                <div style="padding: 20px; background: #f9f9f9; border-radius: 8px; line-height: 1.8;">
                    {% if error_count > 0 %}
                    <p><strong>必须修复以下问题：</strong></p>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        {% for rule_name, count in error_summary.items() %}
                        <li>修复 {{ count }} 个 "{{ rule_name }}" 错误</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                    
                    {% if warning_count > 0 %}
                    <p style="margin-top: 15px;"><strong>建议检查以下问题：</strong></p>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        {% for rule_name, count in warning_summary.items() %}
                        <li>检查 {{ count }} 个 "{{ rule_name }}" 警告</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                    
                    {% if error_count == 0 and warning_count == 0 %}
                    <p>✓ BOM文件质量良好，可以继续流程。</p>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>本报告由PLM只读同步库自动生成</p>
            <p>生成时间: {{ validation_time }}</p>
            <p>© 2026 BOM自动化校验系统</p>
        </div>
    </div>
</body>
</html>"""
