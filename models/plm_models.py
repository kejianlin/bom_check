from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Material(Base):
    """物料主表"""
    __tablename__ = 'materials'
    
    material_code = Column(String(50), primary_key=True, comment='物料编码')
    material_name = Column(String(200), nullable=False, comment='物料名称')
    specification = Column(String(500), comment='规格型号')
    category = Column(String(100), comment='物料类别')
    unit = Column(String(20), comment='计量单位')
    status = Column(String(20), default='active', comment='状态')
    supplier_code = Column(String(50), comment='供应商编码')
    version = Column(String(20), comment='版本')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    remark = Column(Text, comment='备注')
    
    attributes = relationship("MaterialAttribute", back_populates="material", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'material_code': self.material_code,
            'material_name': self.material_name,
            'specification': self.specification,
            'category': self.category,
            'unit': self.unit,
            'status': self.status,
            'supplier_code': self.supplier_code,
            'version': self.version,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'remark': self.remark
        }


class MaterialAttribute(Base):
    """物料属性表"""
    __tablename__ = 'material_attributes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(50), ForeignKey('materials.material_code'), nullable=False, comment='物料编码')
    attribute_name = Column(String(100), nullable=False, comment='属性名称')
    attribute_value = Column(String(500), comment='属性值')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    material = relationship("Material", back_populates="attributes")


class BOMStructure(Base):
    """BOM结构表"""
    __tablename__ = 'bom_structure'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_material = Column(String(50), nullable=False, comment='父物料编码')
    child_material = Column(String(50), nullable=False, comment='子物料编码')
    quantity = Column(Float, nullable=False, comment='数量')
    unit = Column(String(20), comment='单位')
    level = Column(Integer, default=1, comment='层级')
    substitute_material = Column(String(50), comment='替代料编码')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class Supplier(Base):
    """供应商表"""
    __tablename__ = 'suppliers'
    
    supplier_code = Column(String(50), primary_key=True, comment='供应商编码')
    supplier_name = Column(String(200), nullable=False, comment='供应商名称')
    contact = Column(String(100), comment='联系人')
    phone = Column(String(50), comment='电话')
    email = Column(String(100), comment='邮箱')
    address = Column(String(500), comment='地址')
    status = Column(String(20), default='active', comment='状态')
    certification = Column(String(100), comment='认证信息')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class Unit(Base):
    """计量单位表"""
    __tablename__ = 'units'
    
    unit_code = Column(String(20), primary_key=True, comment='单位编码')
    unit_name = Column(String(50), nullable=False, comment='单位名称')
    unit_type = Column(String(50), comment='单位类型')
    conversion_factor = Column(Float, default=1.0, comment='换算系数')
    base_unit = Column(String(20), comment='基准单位')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class SyncLog(Base):
    """同步日志表"""
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_time = Column(DateTime, default=datetime.now, comment='同步时间')
    sync_type = Column(String(20), comment='同步类型: full/incremental')
    table_name = Column(String(100), comment='表名')
    records_synced = Column(Integer, default=0, comment='同步记录数')
    status = Column(String(20), comment='状态: success/failed/warning')
    error_message = Column(Text, comment='错误信息')
    duration_seconds = Column(Float, comment='耗时（秒）')
