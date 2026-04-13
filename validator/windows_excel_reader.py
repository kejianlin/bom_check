from pathlib import Path
from typing import List, Optional

import pandas as pd

from utils.logger import get_default_logger

logger = get_default_logger()


class WindowsExcelReader:
    """Use Excel COM automation to read workbooks on Windows."""

    def __init__(self, prog_id: str = "Excel.Application"):
        self.prog_id = prog_id

    def read_dataframe(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        workbook, excel = self._open_workbook(file_path)
        try:
            worksheet = self._select_worksheet(workbook, sheet_name)
            values = worksheet.UsedRange.Value
            rows = self._normalize_matrix(values)

            if not rows:
                return pd.DataFrame()

            headers = [self._normalize_header(value) for value in rows[0]]
            data_rows = rows[1:] if len(rows) > 1 else []
            return pd.DataFrame(data_rows, columns=headers)
        finally:
            self._close_workbook(workbook, excel)

    def list_sheet_names(self, file_path: str) -> List[str]:
        workbook, excel = self._open_workbook(file_path)
        try:
            return [str(sheet.Name) for sheet in workbook.Worksheets]
        finally:
            self._close_workbook(workbook, excel)

    def _open_workbook(self, file_path: str):
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "Windows 受控读取模式需要安装 pywin32，并且必须运行在 Windows Server 上。"
            ) from exc

        abs_path = str(Path(file_path).resolve())
        pythoncom.CoInitialize()
        excel = None
        workbook = None

        try:
            excel = win32com.client.DispatchEx(self.prog_id)
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.AskToUpdateLinks = False
            workbook = excel.Workbooks.Open(abs_path, 0, True)
            logger.info(f"已通过 Excel COM 打开工作簿: {abs_path}")
            return workbook, excel
        except Exception:
            if workbook is not None:
                try:
                    workbook.Close(False)
                except Exception:
                    pass
            if excel is not None:
                try:
                    excel.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
            raise

    def _close_workbook(self, workbook, excel) -> None:
        import pythoncom

        try:
            if workbook is not None:
                workbook.Close(False)
        finally:
            try:
                if excel is not None:
                    excel.Quit()
            finally:
                pythoncom.CoUninitialize()

    def _select_worksheet(self, workbook, sheet_name: Optional[str]):
        if sheet_name:
            return workbook.Worksheets(sheet_name)
        return workbook.Worksheets(1)

    def _normalize_matrix(self, values) -> List[List[object]]:
        if values is None:
            return []

        if not isinstance(values, tuple):
            return [[values]]

        rows = []
        for row in values:
            if isinstance(row, tuple):
                rows.append(list(row))
            else:
                rows.append([row])
        return rows

    def _normalize_header(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip()
