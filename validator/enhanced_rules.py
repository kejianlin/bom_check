#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版BOM校验规则
支持新的字段结构：父编码、子编码、bomviewaltsuid等
"""

import re
from typing import List, Optional, Any, Dict, Set
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
        self.error_message = rule_config.get('error_message', self.description)
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        """执行校验，返回错误信息或None"""
        raise NotImplementedError("子类必须实现validate方法")
    
    def _get_field_label(self, field_name: str = None) -> str:
        """获取字段的中文标签，默认使用self.field"""
        if field_name is None:
            field_name = self.field
        return BOMItem.get_field_label(field_name)
    
    def create_error(self, item: BOMItem, message: str = None, 
                    expected_value: Any = None, actual_value: Any = None) -> ValidationError:
        """创建错误对象"""
        return ValidationError(
            row_number=item.row_number,
            rule_id=self.rule_id,
            rule_name=self.name,
            severity=self.severity,
            field=self.field,
            message=message or self.error_message,
            expected_value=expected_value,
            actual_value=actual_value
        )


class RequiredCheckRule(ValidationRule):
    """必填字段校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        
        if value is None or (isinstance(value, str) and not value.strip()):
            field_label = self._get_field_label()
            return self.create_error(
                item,
                f"{field_label}({self.field})不能为空",
                expected_value="非空值",
                actual_value=None
            )
        
        return None


class FormatCheckRule(ValidationRule):
    """格式校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        field_label = self._get_field_label()
        
        # 允许为空的情况
        if self.config.get('allow_empty', False) and not value:
            return None
        
        if not value:
            return None
        
        # 正则表达式校验
        pattern = self.config.get('pattern')
        if pattern:
            if not re.match(pattern, str(value)):
                return self.create_error(
                    item,
                    self.error_message,
                    expected_value=f"匹配模式: {pattern}",
                    actual_value=value
                )
        
        # 数值范围校验
        if self.field == 'quantity' or 'min_value' in self.config:
            try:
                num_value = float(value)
                min_val = self.config.get('min_value')
                max_val = self.config.get('max_value')
                
                if min_val is not None and num_value < min_val:
                    return self.create_error(
                        item,
                        f"{field_label}({self.field})必须大于等于{min_val}",
                        expected_value=f">= {min_val}",
                        actual_value=value
                    )
                
                if max_val is not None and num_value > max_val:
                    return self.create_error(
                        item,
                        f"{field_label}({self.field})必须小于等于{max_val}",
                        expected_value=f"<= {max_val}",
                        actual_value=value
                    )
                
                # 小数位数校验
                decimal_places = self.config.get('decimal_places')
                if decimal_places is not None:
                    str_value = str(value)
                    if '.' in str_value:
                        actual_decimals = len(str_value.split('.')[1])
                        if actual_decimals > decimal_places:
                            return self.create_error(
                                item,
                                f"{field_label}({self.field})最多{decimal_places}位小数",
                                expected_value=f"<= {decimal_places}位小数",
                                actual_value=f"{actual_decimals}位小数"
                            )
                
            except (ValueError, TypeError):
                return self.create_error(
                    item,
                    f"{field_label}({self.field})必须是有效的数字",
                    expected_value="数字",
                    actual_value=value
                )
        
        return None


class ExistenceCheckRule(ValidationRule):
    """存在性校验规则（检查PLM系统或数据库）"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        if not value:
            return None
        
        field_label = self._get_field_label()
        check_source = self.config.get('check_source', 'plm_materials')
        
        if check_source == 'plm_materials':
            materials = plm_data.get('materials', {})
            if value not in materials:
                return self.create_error(
                    item,
                    f"{field_label}({self.field})={value}在PLM系统中不存在",
                    expected_value="存在于PLM系统",
                    actual_value=value
                )
        
        elif check_source == 'plm_suppliers':
            suppliers = plm_data.get('suppliers', {})
            if value not in suppliers:
                return self.create_error(
                    item,
                    f"{field_label}({self.field})={value}不在认证供应商列表中",
                    expected_value="认证供应商",
                    actual_value=value
                )
        
        elif check_source == 'db_cpcitem':
            # 从数据库cpcitem表检查
            try:
                from validator.db_validator import get_db_validator
                db_validator = get_db_validator()
                
                if not db_validator.check_item_code_exists(value):
                    return self.create_error(
                        item,
                        f"{field_label}({self.field})={value}在数据库cpcitem表中不存在",
                        expected_value="存在于cpcitem.ITEMCODE",
                        actual_value=value
                    )
                
                # 检查子编码是否禁用或停产（ITEMNAME包含"禁用"、"停产"）
                if self.config.get('check_disabled', False):
                    is_disabled = db_validator.check_item_disabled_or_discontinued(value)
                    if is_disabled:
                        return self.create_error(
                            item,
                            f"子编码{value}禁用或停产不可用",
                            expected_value="物料名称不包含禁用、停产",
                            actual_value=value
                        )
            except Exception as e:
                logger.error(f"数据库检查失败: {str(e)}")
                # 数据库检查失败时，记录警告但不阻止验证
                return None
        
        return None


class WhitelistCheckRule(ValidationRule):
    """白名单校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        
        # 允许为空的情况
        if self.config.get('allow_empty', False) and not value:
            return None
        
        if not value:
            return None
        
        # 从配置中获取白名单
        whitelist = self.config.get('whitelist', [])
        
        # 或从PLM数据中获取
        check_source = self.config.get('check_source')
        if check_source == 'plm_units':
            whitelist = [unit['unit_code'] for unit in plm_data.get('units', {}).values()]
        
        if whitelist and value not in whitelist:
            return self.create_error(
                item,
                self.error_message,
                expected_value=f"允许值: {', '.join(map(str, whitelist[:10]))}",
                actual_value=value
            )
        
        return None


class ConsistencyCheckRule(ValidationRule):
    """一致性校验规则（与PLM系统对比）"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        # 获取参考字段（通常是物料编码）
        reference_field = self.config.get('reference_field', 'child_code')
        reference_value = getattr(item, reference_field, None)
        
        if not reference_value:
            return None
        
        field_label = self._get_field_label()
        
        # 从PLM系统获取数据
        check_source = self.config.get('check_source', 'plm_materials')
        materials = plm_data.get('materials', {})
        material = materials.get(reference_value)
        
        if not material:
            return None
        
        # 获取实际值和期望值
        actual_value = getattr(item, self.field, None)
        expected_value = material.get(self.field)
        
        if not actual_value or not expected_value:
            return None
        
        actual_str = str(actual_value).strip()
        expected_str = str(expected_value).strip()
        
        # 完全一致性检查
        tolerance = self.config.get('tolerance', 1.0)
        
        if tolerance >= 1.0:
            # 必须完全一致
            if actual_str != expected_str:
                return self.create_error(
                    item,
                    f"{field_label}({self.field})与PLM系统不一致",
                    expected_value=expected_str,
                    actual_value=actual_str
                )
        else:
            # 相似度检查
            similarity = SequenceMatcher(None, actual_str, expected_str).ratio()
            if similarity < tolerance:
                return self.create_error(
                    item,
                    f"{field_label}({self.field})与PLM系统不一致（相似度: {similarity:.1%}）",
                    expected_value=expected_str,
                    actual_value=actual_str
                )
        
        return None


class DbUnitConsistencyCheckRule(ValidationRule):
    """数据库单位一致性校验规则 - 检查上传文件中的子编码单位与数据库中是否一致"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        # 获取参考字段（通常是子编码child_code）
        reference_field = self.config.get('reference_field', 'child_code')
        reference_value = getattr(item, reference_field, None)
        
        if not reference_value:
            return None
        
        # 获取要检查的字段（通常是单位unit）
        check_field = self.config.get('check_field', 'unit')
        actual_value = getattr(item, check_field, None)
        check_field_label = self._get_field_label(check_field)
        
        if not actual_value:
            return None
        
        # 从数据库获取子编码的标准单位
        try:
            from validator.db_validator import DBValidator
            db_validator = DBValidator()
            
            # 获取物料详细信息
            item_info = db_validator.get_item_info(str(reference_value))
            
            if not item_info:
                # 物料不存在，返回错误
                return self.create_error(
                    item,
                    f"子编码{reference_value}在数据库中不存在，无法校验{check_field_label}",
                    expected_value="存在于数据库",
                    actual_value=reference_value
                )
            
            # 获取数据库中的标准单位
            db_unit = item_info.get('unit')
            
            if not db_unit:
                # 数据库中没有单位信息
                return self.create_error(
                    item,
                    f"子编码{reference_value}在数据库中的{check_field_label}({check_field})信息为空",
                    expected_value="非空值",
                    actual_value=db_unit
                )
            
            # 比较单位
            actual_str = str(actual_value).strip()
            db_str = str(db_unit).strip()
            
            # 大小写不敏感比较
            if actual_str.upper() != db_str.upper():
                # 获取子编码的物料名称，用于错误信息
                item_name = item_info.get('item_name', '未知物料')
                
                return self.create_error(
                    item,
                    f"子编码{reference_value}({item_name})的{check_field_label}({check_field})不一致",
                    expected_value=f"数据库{check_field_label}: {db_str}",
                    actual_value=f"上传文件{check_field_label}: {actual_str}"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"数据库查询失败: {str(e)}")
            # 数据库查询失败时，根据配置判断是否报错
            if self.config.get('fail_on_db_error', False):
                return self.create_error(
                    item,
                    f"数据库查询失败: {str(e)}",
                    expected_value="成功查询数据库",
                    actual_value="查询失败"
                )
            # 否则返回None，允许继续验证
            return None


class PBSChildCodeRestrictRule(ValidationRule):
    """PBS前缀子编码限制规则 - 检查以PBS开头的父编码下不能出现指定前缀的子编码"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        parent_code = getattr(item, 'parent_code', None)
        child_code = getattr(item, 'child_code', None)
        
        if not parent_code or not child_code:
            return None
        
        # 检查父编码是否以PBS开头
        parent_code_upper = str(parent_code).upper()
        if not parent_code_upper.startswith('PBS'):
            return None
        
        # 获取禁止的子编码前缀列表
        forbidden_prefixes = self.config.get('forbidden_prefixes', ['RED', 'CAD', 'TRD', 'ICD', 'MGD'])
        
        # 检查子编码是否以禁止的前缀开头
        child_code_upper = str(child_code).upper()
        for prefix in forbidden_prefixes:
            if child_code_upper.startswith(prefix):
                return self.create_error(
                    item,
                    f"父编码{parent_code}以PBS开头，子编码不能以{prefix}开头",
                    expected_value=f"子编码不以 {','.join(forbidden_prefixes)} 开头",
                    actual_value=f"{child_code}（以{prefix}开头）"
                )
        
        return None


class PCAChildCodeRestrictRule(ValidationRule):
    """PCA前缀子编码限制规则 - 检查以PCA开头的父编码下不能出现指定前缀的子编码"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        parent_code = getattr(item, 'parent_code', None)
        child_code = getattr(item, 'child_code', None)
        
        if not parent_code or not child_code:
            return None
        
        # 检查父编码是否以PCA开头
        parent_code_upper = str(parent_code).upper()
        if not parent_code_upper.startswith('PCA'):
            return None
        
        # 获取禁止的子编码前缀列表
        forbidden_prefixes = self.config.get('forbidden_prefixes', ['RES', 'CAS', 'TRS', 'ICS', 'MGS'])
        
        # 检查子编码是否以禁止的前缀开头
        child_code_upper = str(child_code).upper()
        for prefix in forbidden_prefixes:
            if child_code_upper.startswith(prefix):
                return self.create_error(
                    item,
                    f"父编码{parent_code}以PCA开头，子编码不能以{prefix}开头",
                    expected_value=f"子编码不以 {','.join(forbidden_prefixes)} 开头",
                    actual_value=f"{child_code}（以{prefix}开头）"
                )
        
        return None


class LogicCheckRule(ValidationRule):
    """逻辑校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        check_type = self.config.get('check_type')
        fields = self.config.get('fields', [])
        
        if check_type == 'not_equal':
            # 检查两个字段不能相等
            if len(fields) >= 2:
                value1 = getattr(item, fields[0], None)
                value2 = getattr(item, fields[1], None)
                
                if value1 and value2 and value1 == value2:
                    return self.create_error(
                        item,
                        self.error_message,
                        expected_value=f"{fields[0]} ≠ {fields[1]}",
                        actual_value=f"{value1} = {value2}"
                    )
        
        return None


class DuplicateCheckRule(ValidationRule):
    """重复性校验规则"""
    
    def __init__(self, rule_config: dict):
        super().__init__(rule_config)
        self.seen_combinations: Set[tuple] = set()
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        check_fields = self.config.get('check_fields', [self.field])
        
        # 获取组合键
        values = tuple(getattr(item, field, None) for field in check_fields)
        
        # 如果有空值，跳过检查
        if None in values or '' in values:
            return None
        
        if values in self.seen_combinations:
            # 生成带有字段标签的错误信息
            fields_str = ', '.join(
                f"{self._get_field_label(field)}({field})={val}" 
                for field, val in zip(check_fields, values)
            )
            return self.create_error(
                item,
                f"重复的组合: {fields_str}",
                expected_value="唯一组合",
                actual_value=fields_str
            )
        
        self.seen_combinations.add(values)
        return None
    
    def reset(self):
        """重置状态"""
        self.seen_combinations.clear()


class CircularCheckRule(ValidationRule):
    """循环引用检查规则"""
    
    def __init__(self, rule_config: dict):
        super().__init__(rule_config)
        self.bom_structure: Dict[str, List[str]] = {}
    
    def add_item(self, item: BOMItem):
        """添加BOM项到结构中"""
        parent = item.parent_code
        child = item.child_code
        
        if parent and child:
            if parent not in self.bom_structure:
                self.bom_structure[parent] = []
            self.bom_structure[parent].append(child)
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        self.add_item(item)
        
        # 检查是否存在循环引用
        parent = item.parent_code
        child = item.child_code
        
        if self._has_circular_reference(child, parent, set()):
            return self.create_error(
                item,
                f"检测到循环引用: {parent} -> {child}",
                expected_value="无循环引用",
                actual_value=f"{parent} -> {child}"
            )
        
        return None
    
    def _has_circular_reference(self, current: str, target: str, visited: Set[str]) -> bool:
        """递归检查循环引用"""
        if current == target:
            return True
        
        if current in visited:
            return False
        
        visited.add(current)
        
        children = self.bom_structure.get(current, [])
        for child in children:
            if self._has_circular_reference(child, target, visited.copy()):
                return True
        
        return False
    
    def reset(self):
        """重置状态"""
        self.bom_structure.clear()


class StatusCheckRule(ValidationRule):
    """状态校验规则"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        if not value:
            return None
        
        check_source = self.config.get('check_source', 'plm_materials')
        materials = plm_data.get('materials', {})
        material = materials.get(value)
        
        if not material:
            return None
        
        field_label = self._get_field_label()
        allowed_status = self.config.get('allowed_status', [])
        current_status = material.get('status')
        
        if current_status and current_status not in allowed_status:
            return self.create_error(
                item,
                f"{field_label}({self.field})={value}状态为{current_status}，不允许使用",
                expected_value=f"允许状态: {', '.join(allowed_status)}",
                actual_value=current_status
            )
        
        return None


class UniqueCheckRule(ValidationRule):
    """唯一性校验规则（在同一父编码下）"""
    
    def __init__(self, rule_config: dict):
        super().__init__(rule_config)
        self.parent_values: Dict[str, Set[Any]] = {}
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        parent_field = self.config.get('parent_field', 'parent_code')
        check_field = self.config.get('check_field', self.field)
        allow_empty = self.config.get('allow_empty', False)
        
        parent_value = getattr(item, parent_field, None)
        check_value = getattr(item, check_field, None)
        
        if not parent_value:
            return None
        
        if allow_empty and not check_value:
            return None
        
        if not check_value:
            return None
        
        # 初始化父编码的值集合
        if parent_value not in self.parent_values:
            self.parent_values[parent_value] = set()
        
        # 检查是否重复
        if check_value in self.parent_values[parent_value]:
            check_field_label = self._get_field_label(check_field)
            return self.create_error(
                item,
                f"在父编码{parent_value}下，{check_field_label}({check_field})={check_value}重复",
                expected_value="唯一值",
                actual_value=check_value
            )
        
        self.parent_values[parent_value].add(check_value)
        return None
    
    def reset(self):
        """重置状态"""
        self.parent_values.clear()


class NoSpaceCheckRule(ValidationRule):
    """空格检查规则 - 检查字段中是否包含空格"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        value = getattr(item, self.field, None)
        field_label = self._get_field_label()
        
        # 允许为空的情况
        if self.config.get('allow_empty', False) and not value:
            return None
        
        if not value:
            return None
        
        # 转换为字符串并检查是否包含空格
        str_value = str(value).strip()
        if ' ' in str_value:
            return self.create_error(
                item,
                f"{field_label}({self.field})不能包含空格",
                expected_value="无空格",
                actual_value=str_value
            )
        
        return None


class PositionQtyMatchRule(ValidationRule):
    """位置号与用量匹配规则 - 检查特定前缀(PCA/PBS/PAI)的父编码是否用量与位置号数量匹配"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        parent_code = getattr(item, 'parent_code', None)
        position_number = getattr(item, 'position_number', None)
        quantity = getattr(item, 'quantity', None)
        
        # 检查是否需要进行校验（检查父编码前缀）
        check_prefixes = self.config.get('check_prefixes', ['PCA', 'PBS', 'PAI'])
        should_check = False
        
        if parent_code:
            parent_code_upper = str(parent_code).upper()
            for prefix in check_prefixes:
                if parent_code_upper.startswith(prefix):
                    should_check = True
                    break
        
        # 如果不符合检查条件，直接通过
        if not should_check:
            return None
        
        # 如果位置号为空，根据配置判断是否允许
        if not position_number:
            if self.config.get('allow_empty_position', False):
                return None
            else:
                position_label = self._get_field_label('position_number')
                return self.create_error(
                    item,
                    f"父编码{parent_code}以{','.join(check_prefixes)}开头，{position_label}(position_number)不能为空",
                    expected_value="非空位置号（逗号分隔）",
                    actual_value=None
                )
        
        # 如果用量为空
        if quantity is None:
            quantity_label = self._get_field_label('quantity')
            return self.create_error(
                item,
                f"父编码{parent_code}以{','.join(check_prefixes)}开头，{quantity_label}(quantity)不能为空",
                expected_value="正整数",
                actual_value=None
            )
        
        # 解析位置号（逗号或其他分隔符）
        separator = self.config.get('separator', ',')
        position_str = str(position_number).strip()
        
        # 分割位置号
        positions = [p.strip() for p in position_str.split(separator) if p.strip()]
        position_count = len(positions)
        
        # 获取用量的期望值
        try:
            quantity_value = float(quantity)
            quantity_int = int(quantity_value)
        except (ValueError, TypeError):
            quantity_label = self._get_field_label('quantity')
            return self.create_error(
                item,
                f"{quantity_label}(quantity)必须是有效的数字",
                expected_value="数字",
                actual_value=quantity
            )
        
        # 检查用量是否等于位置号数量
        position_label = self._get_field_label('position_number')
        quantity_label = self._get_field_label('quantity')
        
        if quantity_int != position_count:
            return self.create_error(
                item,
                f"{position_label}(position_number)数量({position_count})与{quantity_label}(quantity)({quantity_int})不匹配",
                expected_value=f"{quantity_label}数={position_count}（{position_label}数量）",
                actual_value=f"{quantity_label}={quantity_int}，{position_label}={position_str}"
            )
        
        # 额外检查：验证位置号格式（可选）
        position_pattern = self.config.get('position_pattern')
        if position_pattern:
            for idx, pos in enumerate(positions, 1):
                if not re.match(position_pattern, pos):
                    position_label = self._get_field_label('position_number')
                    return self.create_error(
                        item,
                        f"第{idx}个{position_label}(position_number)'{pos}'格式不符合要求",
                        expected_value=f"匹配模式: {position_pattern}",
                        actual_value=pos
                    )
        
        return None


class ChildCodePositionMatchRule(ValidationRule):
    """子编码与位置号前缀匹配规则 - 检查子编码前缀和位置号前缀是否对应"""
    
    def validate(self, item: BOMItem, plm_data: dict) -> Optional[ValidationError]:
        if not self.enabled:
            return None
        
        child_code = getattr(item, 'child_code', None)
        position_number = getattr(item, 'position_number', None)
        
        if not child_code or not position_number:
            # 允许为空的情况
            if self.config.get('allow_empty_position', True):
                return None
            return None
        
        # 获取应用位模式配置（如果指定则仅对某些父编码应用）
        apply_to_parents = self.config.get('apply_to_parents')
        if apply_to_parents:
            parent_code = getattr(item, 'parent_code', None)
            if not parent_code:
                return None
            
            parent_code_upper = str(parent_code).upper()
            should_check = False
            for prefix in apply_to_parents:
                if parent_code_upper.startswith(prefix):
                    should_check = True
                    break
            
            if not should_check:
                return None
        
        # 获取子编码前缀到位置号前缀的映射规则
        child_to_position_map = self.config.get('child_to_position_map', {})
        if not child_to_position_map:
            return None
        
        child_code_upper = str(child_code).upper()
        position_number_upper = str(position_number).upper()
        
        # 查找匹配的子编码前缀
        matched_position_prefixes = None
        for child_prefix, position_prefixes in child_to_position_map.items():
            child_prefix_upper = child_prefix.upper()
            if child_code_upper.startswith(child_prefix_upper):
                matched_position_prefixes = position_prefixes
                break
        
        # 如果没有找到匹配的子编码前缀，表示不需要检查或规则不适用
        if matched_position_prefixes is None:
            return None
        
        # 检查位置号是否以对应的前缀开头
        # 位置号可能是逗号分隔的多个值
        separator = self.config.get('separator', ',')
        position_values = [p.strip() for p in position_number_upper.split(separator) if p.strip()]
        
        # 确保 matched_position_prefixes 是列表
        if isinstance(matched_position_prefixes, str):
            matched_position_prefixes = [matched_position_prefixes]
        
        # 检查每一个位置号是否以允许的前缀开头
        for pos_value in position_values:
            position_valid = False
            for expected_prefix in matched_position_prefixes:
                expected_prefix_upper = expected_prefix.upper()
                if pos_value.startswith(expected_prefix_upper):
                    position_valid = True
                    break
            
            if not position_valid:
                return self.create_error(
                    item,
                    f"子编码{child_code}以{child_prefix_upper}开头，位置号应以{'/'.join(matched_position_prefixes)}开头，但实际为{pos_value}",
                    expected_value=f"位置号以 {'/'.join(matched_position_prefixes)} 开头",
                    actual_value=pos_value
                )
        
        return None


class RuleFactory:
    """规则工厂"""
    
    RULE_TYPES = {
        'required_check': RequiredCheckRule,
        'format_check': FormatCheckRule,
        'existence_check': ExistenceCheckRule,
        'whitelist_check': WhitelistCheckRule,
        'consistency_check': ConsistencyCheckRule,
        'db_unit_consistency_check': DbUnitConsistencyCheckRule,
        'logic_check': LogicCheckRule,
        'duplicate_check': DuplicateCheckRule,
        'circular_check': CircularCheckRule,
        'status_check': StatusCheckRule,
        'unique_check': UniqueCheckRule,
        'no_space_check': NoSpaceCheckRule,
        'position_qty_match': PositionQtyMatchRule,
        'pbs_child_code_restrict': PBSChildCodeRestrictRule,
        'pca_child_code_restrict': PCAChildCodeRestrictRule,
        'child_code_position_match': ChildCodePositionMatchRule,
    }
    
    @classmethod
    def create_rule(cls, rule_config: dict) -> ValidationRule:
        """创建规则实例"""
        rule_type = rule_config.get('type')
        rule_class = cls.RULE_TYPES.get(rule_type)
        
        if not rule_class:
            logger.warning(f"未知的规则类型: {rule_type}，跳过")
            return None
        
        return rule_class(rule_config)
    
    @classmethod
    def create_rules_from_config(cls, config: dict, mode: str = 'standard') -> List[ValidationRule]:
        """从配置文件创建规则列表"""
        rules = []
        
        # 获取启用的规则组
        validation_modes = config.get('validation_modes', {})
        mode_config = validation_modes.get(mode, {})
        enabled_groups = mode_config.get('enabled_groups', ['basic'])
        
        # 获取规则组配置
        rule_groups = config.get('rule_groups', {})
        enabled_rule_ids = set()
        for group in enabled_groups:
            enabled_rule_ids.update(rule_groups.get(group, []))
        
        # 创建规则实例
        for rule_config in config.get('validation_rules', []):
            rule_id = rule_config.get('id')
            
            # 检查规则是否在启用的组中
            if rule_id not in enabled_rule_ids:
                continue
            
            rule = cls.create_rule(rule_config)
            if rule:
                rules.append(rule)
        
        logger.info(f"已加载{len(rules)}个校验规则（模式: {mode}）")
        return rules
