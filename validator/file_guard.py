from pathlib import Path
import zipfile


XLS_SIGNATURES = (
    bytes.fromhex("D0CF11E0A1B11AE1"),  # OLE Compound File
    bytes.fromhex("0908100000060500"),  # Legacy BIFF (common variant)
)


class ExcelFileGuardError(ValueError):
    """Raised when the uploaded file is not a readable Excel container."""


def _read_header(file_path: Path, size: int = 16) -> bytes:
    with open(file_path, "rb") as f:
        return f.read(size)


def validate_excel_container(file_path: str) -> None:
    """
    Validate whether the file is a readable native Excel container.

    This is mainly used to fail fast on wrapped/encrypted files
    (for example enterprise DLP products such as 绿盾), renamed files,
    or damaged uploads.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in {".xlsx", ".xls"}:
        raise ExcelFileGuardError(f"不支持的文件格式: {suffix}")

    header = _read_header(path)

    if suffix == ".xlsx":
        if not zipfile.is_zipfile(path):
            raise ExcelFileGuardError(_encrypted_excel_message(path.name))

        try:
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
        except zipfile.BadZipFile as exc:
            raise ExcelFileGuardError(_encrypted_excel_message(path.name)) from exc

        required_entries = {"[Content_Types].xml", "xl/workbook.xml"}
        if not required_entries.issubset(names):
            raise ExcelFileGuardError(_encrypted_excel_message(path.name))
        return

    if not any(header.startswith(signature) for signature in XLS_SIGNATURES):
        raise ExcelFileGuardError(_encrypted_excel_message(path.name))


def _encrypted_excel_message(filename: str) -> str:
    return (
        f"文件“{filename}”不是服务端可直接解析的原生 Excel 文件。"
        "它可能已损坏、被修改扩展名，或经过绿盾等文档加密/外发控制处理。"
        "请在具备授权的终端先正常打开并另存为标准 Excel 后再上传；"
        "如果业务必须直接校验加密文件，需要把校验服务部署到已安装并授权绿盾客户端的机器上，"
        "由受信任进程先打开文件，再交给当前系统读取。"
    )
