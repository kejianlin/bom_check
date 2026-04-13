import os
import platform


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_excel_reader_mode() -> str:
    """
    Return the effective Excel reader mode.

    Supported values:
    - plain: use pandas/openpyxl/xlrd to read standard Excel files
    - windows_com: use Excel COM automation on Windows to read files that
      must be opened in an authorized desktop environment such as 绿盾
    - auto: plain on Linux; optional windows_com on Windows when enabled
    """
    mode = os.getenv("BOM_EXCEL_READER_MODE", "auto").strip().lower()
    if mode not in {"auto", "plain", "windows_com"}:
        return "plain"

    if mode == "auto":
        if platform.system().lower() == "windows" and _read_bool("WINDOWS_ENCRYPTED_EXCEL_ENABLED", False):
            return "windows_com"
        return "plain"

    return mode


def is_windows_com_mode() -> bool:
    return get_excel_reader_mode() == "windows_com"


def supports_markup_report() -> bool:
    """
    The markup report modifies a workbook copy with openpyxl, so it is only
    safe when we are dealing with a standard readable Excel container.
    """
    return not is_windows_com_mode()
