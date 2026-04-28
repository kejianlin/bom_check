from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Dict, List, Tuple

from models.bom_models import BOMItem, ValidationError, ValidationResult
from utils.logger import get_default_logger

logger = get_default_logger()


class HTMLMarkupGenerator:
    """HTML 标注报告生成器 - 在线查看原始数据及错误标注"""

    FIELD_ORDER_FALLBACK = [
        "parent_code",
        "bomviewaltsuid",
        "child_code",
        "quantity",
        "position_number",
        "order_type",
        "work_order_category",
        "unit",
        "material_name",
        "specification",
        "supplier",
        "remark",
        "version",
        "substitute",
    ]

    def generate(self, result: ValidationResult, output_path: str):
        logger.info(f"开始生成HTML标注报告: {output_path}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        html = self._render(result)
        output_file.write_text(html, encoding="utf-8")
        logger.info(f"HTML标注报告生成成功: {output_path}")

    def _render(self, result: ValidationResult) -> str:
        columns = self._resolve_columns(result.items)
        issues_by_row, issues_by_row_field = self._group_issues(result)
        error_summary = result.get_error_summary()
        warning_summary = result.get_warning_summary()

        header_html = "".join(
            f"<th>{escape(BOMItem.get_field_label(col))}<span>{escape(col)}</span></th>"
            for col in columns
        )

        rows_html = []
        for item in result.items:
            row_issues = issues_by_row.get(item.row_number, [])
            row_field_issues = issues_by_row_field.get(item.row_number, {})
            row_status = self._row_status(row_issues)

            cell_html = []
            for col in columns:
                raw_value = item.raw_data.get(col) if item.raw_data else getattr(item, col, "")
                display_value = "" if raw_value is None else str(raw_value)
                field_issues = row_field_issues.get(col, [])
                classes = []
                if any(issue.severity == "error" for issue in field_issues):
                    classes.append("cell-error")
                elif any(issue.severity == "warning" for issue in field_issues):
                    classes.append("cell-warning")

                title = "&#10;".join(
                    escape(f"[{issue.rule_id}] {issue.message}") for issue in field_issues
                )
                title_attr = f' title="{title}"' if title else ""
                class_attr = f' class="{" ".join(classes)}"' if classes else ""
                cell_html.append(
                    f"<td{class_attr}{title_attr}><div class=\"cell-value\">{escape(display_value)}</div></td>"
                )

            issue_blocks = []
            for issue in row_issues:
                severity_class = "issue-error" if issue.severity == "error" else "issue-warning"
                expected = f"<div class=\"issue-meta\"><strong>期望:</strong> {escape(str(issue.expected_value))}</div>" if issue.expected_value is not None else ""
                actual = f"<div class=\"issue-meta\"><strong>实际:</strong> {escape(str(issue.actual_value))}</div>" if issue.actual_value is not None else ""
                issue_blocks.append(
                    "<div class=\"issue-card {severity}\">"
                    "<div class=\"issue-title\">[{rule_id}] {message}</div>"
                    "{expected}{actual}"
                    "</div>".format(
                        severity=severity_class,
                        rule_id=escape(issue.rule_id),
                        message=escape(issue.message),
                        expected=expected,
                        actual=actual,
                    )
                )

            rows_html.append(
                "<tr class=\"{row_class}\">"
                "<td class=\"row-number\">{row_number}</td>"
                "<td class=\"row-status\"><span class=\"status-pill {status_class}\">{status_text}</span></td>"
                "{cells}"
                "<td class=\"issue-column\">{issues}</td>"
                "</tr>".format(
                    row_class=row_status,
                    row_number=item.row_number,
                    status_class=row_status,
                    status_text=self._row_status_text(row_status),
                    cells="".join(cell_html),
                    issues="".join(issue_blocks) or "<span class=\"issue-empty\">无</span>",
                )
            )

        error_summary_html = self._render_summary_list(error_summary, "error-chip")
        warning_summary_html = self._render_summary_list(warning_summary, "warning-chip")

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML标注报告 - {escape(result.file_name)}</title>
    <style>
        :root {{
            --bg: #0f1720;
            --panel: #132131;
            --panel-soft: #18293c;
            --line: rgba(123, 150, 174, 0.24);
            --text: #e8eef5;
            --muted: #95a6b5;
            --success: #2cb67d;
            --warn: #f3a712;
            --danger: #ed6a5a;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            background: linear-gradient(180deg, #0d151d 0%, #101a25 100%);
            color: var(--text);
        }}
        .page {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 28px;
        }}
        .hero {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 24px 28px;
            margin-bottom: 20px;
        }}
        .hero h1 {{
            margin: 0 0 10px;
            font-size: 28px;
        }}
        .hero p {{
            margin: 0;
            color: var(--muted);
            line-height: 1.7;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 14px;
            margin: 18px 0 0;
        }}
        .stat-card {{
            background: var(--panel-soft);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 18px;
        }}
        .stat-card .label {{
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .stat-card .value {{
            font-size: 28px;
            font-weight: 700;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 20px 22px;
        }}
        .summary-card h2 {{
            margin: 0 0 14px;
            font-size: 18px;
        }}
        .chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .chip {{
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 13px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .error-chip {{ background: rgba(237, 106, 90, 0.16); color: #ffd6d1; }}
        .warning-chip {{ background: rgba(243, 167, 18, 0.16); color: #ffe2a8; }}
        .table-shell {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 20px;
            overflow: hidden;
        }}
        .table-toolbar {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--line);
            color: var(--muted);
            font-size: 14px;
        }}
        .table-wrap {{
            overflow: auto;
            max-height: calc(100vh - 180px);
        }}
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            min-width: 1280px;
        }}
        thead th {{
            position: sticky;
            top: 0;
            z-index: 2;
            background: #0f1b28;
            color: #dcebfa;
            text-align: left;
            padding: 14px 12px;
            border-bottom: 1px solid var(--line);
            font-size: 13px;
            vertical-align: bottom;
        }}
        thead th span {{
            display: block;
            color: var(--muted);
            font-size: 11px;
            margin-top: 4px;
        }}
        tbody td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            vertical-align: top;
            font-size: 13px;
        }}
        tbody tr.row-error {{ background: rgba(237, 106, 90, 0.06); }}
        tbody tr.row-warning {{ background: rgba(243, 167, 18, 0.05); }}
        tbody tr.row-ok {{ background: transparent; }}
        .row-number {{
            white-space: nowrap;
            color: #bfd0df;
            font-weight: 700;
        }}
        .status-pill {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 58px;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }}
        .status-pill.row-error {{ background: rgba(237, 106, 90, 0.18); color: #ffd2cc; }}
        .status-pill.row-warning {{ background: rgba(243, 167, 18, 0.18); color: #ffe2aa; }}
        .status-pill.row-ok {{ background: rgba(44, 182, 125, 0.18); color: #c9f3df; }}
        .cell-error {{
            background: rgba(237, 106, 90, 0.16);
            box-shadow: inset 0 0 0 1px rgba(237, 106, 90, 0.38);
        }}
        .cell-warning {{
            background: rgba(243, 167, 18, 0.15);
            box-shadow: inset 0 0 0 1px rgba(243, 167, 18, 0.34);
        }}
        .cell-value {{
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.6;
        }}
        .issue-column {{
            min-width: 420px;
        }}
        .issue-card {{
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 10px;
            line-height: 1.6;
        }}
        .issue-error {{
            background: rgba(237, 106, 90, 0.14);
            border: 1px solid rgba(237, 106, 90, 0.28);
        }}
        .issue-warning {{
            background: rgba(243, 167, 18, 0.14);
            border: 1px solid rgba(243, 167, 18, 0.28);
        }}
        .issue-title {{
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .issue-meta {{
            color: #d7e4ef;
            font-size: 12px;
        }}
        .issue-empty {{
            color: var(--muted);
        }}
        @media (max-width: 980px) {{
            .stats, .summary-grid {{
                grid-template-columns: 1fr;
            }}
            .page {{ padding: 18px; }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <section class="hero">
            <h1>HTML 标注报告</h1>
            <p>{escape(result.file_name)} | 校验时间：{escape(result.validation_time.strftime("%Y-%m-%d %H:%M:%S"))}</p>
            <div class="stats">
                <div class="stat-card"><div class="label">总行数</div><div class="value">{result.total_rows}</div></div>
                <div class="stat-card"><div class="label">有效行数</div><div class="value">{result.valid_rows}</div></div>
                <div class="stat-card"><div class="label">错误数</div><div class="value" style="color: var(--danger);">{result.error_count}</div></div>
                <div class="stat-card"><div class="label">警告数</div><div class="value" style="color: var(--warn);">{result.warning_count}</div></div>
                <div class="stat-card"><div class="label">通过率</div><div class="value" style="color: var(--success);">{result.pass_rate:.2f}%</div></div>
            </div>
        </section>

        <section class="table-shell">
            <div class="table-toolbar">在线查看原始数据与校验标注。红色表示错误，黄色表示警告；鼠标悬停到高亮单元格可查看对应规则提示。</div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>行号</th>
                            <th>状态</th>
                            {header_html}
                            <th>问题说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(rows_html) if rows_html else '<tr><td colspan="999">没有可展示的数据</td></tr>'}
                    </tbody>
                </table>
            </div>
        </section>
    </div>
</body>
</html>"""

    def _resolve_columns(self, items: List[BOMItem]) -> List[str]:
        if items and items[0].raw_data:
            return list(items[0].raw_data.keys())

        return list(self.FIELD_ORDER_FALLBACK)

    def _group_issues(
        self, result: ValidationResult
    ) -> Tuple[Dict[int, List[ValidationError]], Dict[int, Dict[str, List[ValidationError]]]]:
        issues_by_row: Dict[int, List[ValidationError]] = defaultdict(list)
        issues_by_row_field: Dict[int, Dict[str, List[ValidationError]]] = defaultdict(lambda: defaultdict(list))

        for issue in result.errors + result.warnings:
            issues_by_row[issue.row_number].append(issue)
            target_fields = list(issue.highlight_fields or [])
            if issue.field and issue.field not in target_fields:
                target_fields.insert(0, issue.field)
            for field in target_fields:
                issues_by_row_field[issue.row_number][field].append(issue)

        return issues_by_row, issues_by_row_field

    def _row_status(self, issues: List[ValidationError]) -> str:
        if any(issue.severity == "error" for issue in issues):
            return "row-error"
        if any(issue.severity == "warning" for issue in issues):
            return "row-warning"
        return "row-ok"

    def _row_status_text(self, row_status: str) -> str:
        if row_status == "row-error":
            return "错误"
        if row_status == "row-warning":
            return "警告"
        return "通过"

    def _render_summary_list(self, summary: Dict[str, int], css_class: str) -> str:
        if not summary:
            return ""
        return "".join(
            f"<span class=\"chip {css_class}\">{escape(rule)}：{count}</span>"
            for rule, count in summary.items()
        )
