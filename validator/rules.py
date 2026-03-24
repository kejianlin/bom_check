import re
from typing import List, Optional, Any
from difflib import SequenceMatcher
from models.bom_models import BOMItem, ValidationError
from utils.logger import get_default_logger

logger = get_default_logger()


class ValidationRule:
    """校验规则基类"""
    
    def __init__(self, rule_config: dict):
        self.rule_id = rule_config['id']
        self.name = rule_config['name']
        self.description = rule_config['description']
        self.type = rule_config['type']
        self.enabled = rule_config.get('enabled', True)
        self.severity = rule_config.get('severity', 'error')
        self.field = rule_config.get('field')
        self.config = rule_config
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        """执行校验，返回错误信息或None"""
        raise NotImplementedError("子类必须实现validate方法")


class ExistenceCheckRule(ValidationRule):
    """存在性校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        if not value:
            return ValidationError(
                row_number=item.row_number,
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                field=self.field,
                message=f"{self.description}: 字段为空",
                expected_value="非空值",
                actual_value=None
            )
        
        if self.field == 'material_code':
            material = plm_data.get('materials', {}).get(value)
            if not material:
                return ValidationError(
                    row_number=item.row_number,
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    field=self.field,
                    message=f"物料编码 {value} 在PLM系统中不存在",
                    expected_value="存在于PLM系统",
                    actual_value=value
                )
        
        elif self.field == 'supplier':
            if value:
                supplier = plm_data.get('suppliers', {}).get(value)
                if not supplier:
                    return ValidationError(
                        row_number=item.row_number,
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        severity=self.severity,
                        field=self.field,
                        message=f"供应商 {value} 不在认证供应商列表中",
                        expected_value="认证供应商",
                        actual_value=value
                    )
        
        return None


class ConsistencyCheckRule(ValidationRule):
    """一致性校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        material_code = item.material_code
        material = plm_data.get('materials', {}).get(material_code)
        
        if not material:
            return None
        
        actual_value = getattr(item, self.field, None)
        expected_value = material.get(self.field)
        
        if not actual_value or not expected_value:
            return None
        
        actual_str = str(actual_value).strip()
        expected_str = str(expected_value).strip()
        
        if actual_str == expected_str:
            return None
        
        tolerance = self.config.get('tolerance', 1.0)
        similarity = SequenceMatcher(None, actual_str, expected_str).ratio()
        
        if similarity < tolerance:
            return ValidationError(
                row_number=item.row_number,
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                field=self.field,
                message=f"{self.description}: 不一致（相似度: {similarity:.2%}）",
                expected_value=expected_str,
                actual_value=actual_str
            )
        
        return None


class FormatCheckRule(ValidationRule):
    """格式校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        
        if self.field == 'quantity':
            if value is None:
                return ValidationError(
                    row_number=item.row_number,
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    field=self.field,
                    message="数量字段为空或格式错误",
                    expected_value="正数",
                    actual_value=value
                )
            
            if value <= 0:
                return ValidationError(
                    row_number=item.row_number,
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    field=self.field,
                    message=f"数量必须大于0",
                    expected_value="> 0",
                    actual_value=value
                )
        
        pattern = self.config.get('pattern')
        if pattern and value:
            if not re.match(pattern, str(value)):
                return ValidationError(
                    row_number=item.row_number,
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    field=self.field,
                    message=f"格式不符合要求",
                    expected_value=f"匹配模式: {pattern}",
                    actual_value=value
                )
        
        return None


class WhitelistCheckRule(ValidationRule):
    """白名单校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        
        if not value:
            return None
        
        if self.field == 'unit':
            valid_units = [unit['unit_code'] for unit in plm_data.get('units', {}).values()]
            
            if value not in valid_units:
                return ValidationError(
                    row_number=item.row_number,
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    field=self.field,
                    message=f"单位 {value} 不在允许的单位列表中",
                    expected_value=f"允许的单位: {', '.join(valid_units[:10])}...",
                    actual_value=value
                )
        
        return None


class DuplicateCheckRule(ValidationRule):
    """重复性校验规则"""
    
    def __init__(self, rule_config: dict):
        super().__init__(rule_config)
        self.seen_values = set()
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        
        if not value:
            return None
        
        if value in self.seen_values:
            return ValidationError(
                row_number=item.row_number,
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                field=self.field,
                message=f"物料编码 {value} 在BOM中重复出现",
                expected_value="唯一值",
                actual_value=value
            )
        
        self.seen_values.add(value)
        return None
    
    def reset(self):
        """重置状态"""
        self.seen_values.clear()


class StatusCheckRule(ValidationRule):
    """状态校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        material_code = item.material_code
        material = plm_data.get('materials', {}).get(material_code)
        
        if not material:
            return None
        
        allowed_status = self.config.get('allowed_status', ['active', 'approved'])
        current_status = material.get('status')
        
        if current_status not in allowed_status:
            return ValidationError(
                row_number=item.row_number,
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                field=self.field,
                message=f"物料 {material_code} 状态为 {current_status}，不允许使用",
                expected_value=f"允许的状态: {', '.join(allowed_status)}",
                actual_value=current_status
            )
        
        return None


class RuleFactory:
    """规则工厂"""
    
    RULE_TYPES = {
        'existence_check': ExistenceCheckRule,
        'consistency_check': ConsistencyCheckRule,
        'format_check': FormatCheckRule,
        'whitelist_check': WhitelistCheckRule,
        'duplicate_check': DuplicateCheckRule,
        'status_check': StatusCheckRule,
    }
    
    @classmethod
    def create_rule(cls, rule_config: dict) -> ValidationRule:
        """创建规则实例"""
        rule_type = rule_config.get('type')
        rule_class = cls.RULE_TYPES.get(rule_type)
        
        if not rule_class:
            raise ValueError(f"未知的规则类型: {rule_type}")
        
        return rule_class(rule_config)
