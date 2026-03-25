from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class BOMItem:
    """BOM条目"""
    row_number: int
    parent_code: str
    child_code: str
    material_name: str = None
    bomviewaltsuid: Optional[str] = None
    quantity: Optional[float] = None
    position_number: Optional[str] = None
    order_type: Optional[str] = None
    work_order_category: Optional[str] = None
    unit: Optional[str] = None
    specification: Optional[str] = None
    supplier: Optional[str] = None
    remark: Optional[str] = None
    version: Optional[str] = None
    substitute: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # 字段标签映射 - 用于错误消息显示
    FIELD_LABELS = {
        'parent_code': '父编码',
        'child_code': '子编码',
        'material_name': '物料名称',
        'bomviewaltsuid': 'bomviewaltsuid',
        'quantity': '用量',
        'position_number': '位置号',
        'order_type': '单别',
        'work_order_category': '工单类别',
        'unit': '单位',
        'specification': '规格型号',
        'supplier': '供应商',
        'remark': '备注',
        'version': '版本',
        'substitute': '替代件'
    }
    
    @property
    def material_code(self) -> str:
        """兼容旧代码，返回子编码"""
        return self.child_code
    
    @staticmethod
    def get_field_label(field_name: str) -> str:
        """获取字段的中文标签"""
        return BOMItem.FIELD_LABELS.get(field_name, field_name)


@dataclass
class ValidationError:
    """校验错误"""
    row_number: int
    rule_id: str
    rule_name: str
    severity: str  # error, warning, info
    field: str
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    highlight_fields: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """校验结果"""
    file_name: str
    validation_time: datetime
    total_rows: int
    valid_rows: int
    error_count: int
    warning_count: int
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    items: List[BOMItem] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """是否通过校验（无错误）"""
        return self.error_count == 0
    
    @property
    def pass_rate(self) -> float:
        """通过率"""
        if self.total_rows == 0:
            return 0.0
        return (self.valid_rows / self.total_rows) * 100
    
    def get_error_summary(self) -> Dict[str, int]:
        """获取错误统计"""
        summary = {}
        for error in self.errors:
            if error.rule_name not in summary:
                summary[error.rule_name] = 0
            summary[error.rule_name] += 1
        return summary
    
    def get_warning_summary(self) -> Dict[str, int]:
        """获取警告统计"""
        summary = {}
        for warning in self.warnings:
            if warning.rule_name not in summary:
                summary[warning.rule_name] = 0
            summary[warning.rule_name] += 1
        return summary


def get_connection_string(db_config: Dict[str, Any]) -> str:
    """构建数据库连接字符串"""
    db_type = db_config['type'].lower()
    username = db_config['username']
    password = db_config['password']
    host = db_config['host']
    port = db_config['port']
    database = db_config['database']
    
    if db_type == 'mysql':
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    elif db_type == 'postgresql':
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
    elif db_type == 'sqlserver':
        return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    elif db_type == 'oracle':
        return f"oracle+cx_oracle://{username}:{password}@{host}:{port}/{database}"
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def create_db_engine(db_config: Dict[str, Any]):
    """创建数据库引擎"""
    connection_string = get_connection_string(db_config)
    
    engine = create_engine(
        connection_string,
        poolclass=QueuePool,
        pool_size=db_config.get('pool_size', 5),
        max_overflow=db_config.get('max_overflow', 10),
        pool_pre_ping=True,
        echo=False
    )
    
    return engine


def test_connection(engine) -> bool:
    """测试数据库连接"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False
