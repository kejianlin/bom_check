import yaml
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from models.bom_models import BOMItem, ValidationError, ValidationResult
from validator.enhanced_rules import RuleFactory, ValidationRule
from validator.data_checker import PLMDataChecker
from validator.bom_reader import BOMReader
from utils.logger import get_default_logger

logger = get_default_logger()


class ValidationEngine:
    """BOM校验引擎"""
    
    def __init__(self, config_path: str = "config/validation_rules"):
        self.config_path = config_path
        self.config = self._load_config()
        self.rules = self._initialize_rules()
        self.data_checker = PLMDataChecker()
        
        # 获取required_columns，如果为空则使用None让BOMReader使用默认值
        required_cols = self.config.get('required_columns', None)
        if required_cols:
            logger.info(f"从配置加载必填列: {required_cols}")
            self.bom_reader = BOMReader(required_cols)
        else:
            logger.info("使用BOMReader默认必填列")
            self.bom_reader = BOMReader()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载校验配置"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _initialize_rules(self) -> List[ValidationRule]:
        """初始化校验规则"""
        # 使用新的规则加载方式，支持规则分组和验证模式
        validation_mode = self.config.get('default_mode', 'standard')
        rules = RuleFactory.create_rules_from_config(self.config, mode=validation_mode)
        
        logger.info(f"共加载 {len(rules)} 个校验规则（模式: {validation_mode}）")
        return rules
    
    def validate_bom_file(self, file_path: str, sheet_name: str = None) -> ValidationResult:
        """校验BOM文件"""
        logger.info("="*60)
        logger.info(f"开始校验BOM文件: {file_path}")
        logger.info("="*60)
        
        validation_time = datetime.now()
        
        try:
            bom_items = self.bom_reader.read_excel(file_path, sheet_name)
            
            if not bom_items:
                logger.warning("BOM文件为空")
                return ValidationResult(
                    file_name=Path(file_path).name,
                    validation_time=validation_time,
                    total_rows=0,
                    valid_rows=0,
                    error_count=0,
                    warning_count=0
                )
            
            logger.info("正在加载PLM数据...")
            plm_data = self.data_checker.load_plm_data()
            
            logger.info("开始执行校验规则...")
            errors = []
            warnings = []
            valid_rows = 0
            
            for rule in self.rules:
                if hasattr(rule, 'reset'):
                    rule.reset()
            
            for item in bom_items:
                item_errors = []
                item_warnings = []
                
                for rule in self.rules:
                    error = rule.validate(item, plm_data)
                    if error:
                        if error.severity == 'error':
                            item_errors.append(error)
                            errors.append(error)
                        elif error.severity == 'warning':
                            item_warnings.append(error)
                            warnings.append(error)
                
                if not item_errors:
                    valid_rows += 1
            
            result = ValidationResult(
                file_name=Path(file_path).name,
                validation_time=validation_time,
                total_rows=len(bom_items),
                valid_rows=valid_rows,
                error_count=len(errors),
                warning_count=len(warnings),
                errors=errors,
                warnings=warnings,
                items=bom_items
            )
            
            logger.info("="*60)
            logger.info("校验完成")
            logger.info(f"  总行数: {result.total_rows}")
            logger.info(f"  有效行数: {result.valid_rows}")
            logger.info(f"  错误数: {result.error_count}")
            logger.info(f"  警告数: {result.warning_count}")
            logger.info(f"  通过率: {result.pass_rate:.2f}%")
            logger.info("="*60)
            
            return result
            
        except Exception as e:
            logger.error(f"校验BOM文件失败: {str(e)}", exc_info=True)
            raise
    
    def validate_bom_items(self, bom_items: List[BOMItem]) -> ValidationResult:
        """校验BOM条目列表"""
        validation_time = datetime.now()
        
        logger.info("正在加载PLM数据...")
        plm_data = self.data_checker.load_plm_data()
        
        logger.info("开始执行校验规则...")
        errors = []
        warnings = []
        valid_rows = 0
        
        for rule in self.rules:
            if hasattr(rule, 'reset'):
                rule.reset()
        
        for item in bom_items:
            item_errors = []
            
            for rule in self.rules:
                error = rule.validate(item, plm_data)
                if error:
                    if error.severity == 'error':
                        item_errors.append(error)
                        errors.append(error)
                    elif error.severity == 'warning':
                        warnings.append(error)
            
            if not item_errors:
                valid_rows += 1
        
        return ValidationResult(
            file_name="直接校验",
            validation_time=validation_time,
            total_rows=len(bom_items),
            valid_rows=valid_rows,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings,
            items=bom_items
        )
