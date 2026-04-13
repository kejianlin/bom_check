import os
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import yaml
from pathlib import Path
from utils.logger import get_default_logger
from utils.env_loader import load_project_env

logger = get_default_logger()

# Oracle thick模式初始化标志
_oracle_thick_initialized = False

# 初始化oracledb作为cx_Oracle的兼容替代
try:
    import oracledb
    import sys
    # 注册oracledb为cx_Oracle
    sys.modules['cx_Oracle'] = oracledb
    # 设置版本属性以兼容SQLAlchemy
    if not hasattr(oracledb, 'version'):
        oracledb.version = '8.3.0'
    if not hasattr(oracledb, '__version__'):
        oracledb.__version__ = '8.3.0'
    logger.info("已将oracledb注册为cx_Oracle兼容模块")
except ImportError:
    pass


class DatabaseHelper:
    """数据库辅助类"""
    
    def __init__(self, config_path: str = "config/database.yaml"):
        # 确保环境变量已加载
        dotenv_path = load_project_env()
        logger.info(f"已加载环境变量文件: {dotenv_path}")
        
        self.config_path = config_path
        self.engines = {}
        self.session_makers = {}
        self._load_config()
    
    def _load_config(self):
        """加载数据库配置"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            self.config = yaml.safe_load(content)

        unresolved = []
        for db_name, db_config in self.config.items():
            if not isinstance(db_config, dict):
                continue
            for key, value in db_config.items():
                if isinstance(value, str) and "${" in value:
                    unresolved.append(f"{db_name}.{key}={value}")

        if unresolved:
            raise ValueError(
                "数据库配置中的环境变量未正确替换，请检查 .env 或服务启动环境: "
                + "; ".join(unresolved)
            )
    
    def _init_oracle_thick_mode(self):
        """初始化Oracle thick模式（用于Oracle 11g及更早版本）"""
        global _oracle_thick_initialized
        
        if _oracle_thick_initialized:
            return
        
        try:
            import oracledb
            
            # 尝试初始化thick模式
            # 自动检测常见的Oracle客户端路径
            possible_paths = [
                "/opt/oracle/instantclient_19_12",
                "/opt/oracle/instantclient_19_8",
                "/opt/oracle/instantclient_21_1",
                "/opt/oracle/instantclient_11_2",
                "/usr/lib/oracle/19.12/client64/lib",
                "/usr/lib/oracle/12.2/client64/lib",
                "/usr/lib/oracle/11.2/client64/lib",
                r"C:\oracle\instantclient_19_8",
                r"C:\oracle\instantclient_11_2",
                r"C:\app\oracle\product\11.2.0\client_1\bin",
                os.environ.get('ORACLE_CLIENT_LIB'),  # 从环境变量读取
                None  # 让oracledb自动查找
            ]
            
            for lib_path in possible_paths:
                try:
                    if lib_path and not os.path.exists(lib_path):
                        continue
                    oracledb.init_oracle_client(lib_dir=lib_path)
                    logger.info(f"Oracle Thick模式已初始化: {lib_path or '自动检测'}")
                    _oracle_thick_initialized = True
                    return
                except Exception as e:
                    if lib_path:
                        logger.debug(f"尝试路径 {lib_path} 失败: {e}")
                    continue
            
            logger.warning("未初始化Oracle Thick模式，将使用Thin模式（不支持Oracle 11.2及更早版本）")
            logger.warning("如需连接Oracle 11g，请安装Oracle Instant Client并设置ORACLE_CLIENT_LIB环境变量")
        except ImportError:
            logger.warning("未安装oracledb模块")
        except Exception as e:
            logger.warning(f"Oracle Thick模式初始化失败: {e}")
    
    def _build_connection_string(self, db_config: Dict[str, Any]) -> str:
        """构建数据库连接字符串"""
        db_type = db_config['type'].lower()
        host = db_config['host']
        port = db_config['port']
        database = db_config['database']
        username = db_config['username']
        password = db_config['password']
        
        if db_type == 'mysql':
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        elif db_type == 'postgresql':
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'sqlserver':
            return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        elif db_type == 'oracle':
            # 使用python-oracledb，兼容SQLAlchemy 1.4+
            try:
                import oracledb
                import sys
                
                # 设置版本属性（必须在注册到sys.modules之前）
                oracledb.version = '8.3.0'
                oracledb.__version__ = '8.3.0'
                
                # 注册oracledb作为cx_Oracle的替代品（兼容旧版SQLAlchemy）
                sys.modules['cx_Oracle'] = oracledb
                
                # 初始化Oracle thick模式（可选，支持Oracle 11g）
                self._init_oracle_thick_mode()
                
                # 使用cx_oracle dialect（SQLAlchemy 1.x兼容）
                return f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={database}"
            except ImportError:
                raise ImportError("请安装 oracledb: pip install oracledb")
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def get_engine(self, db_name: str):
        """获取数据库引擎"""
        if db_name in self.engines:
            return self.engines[db_name]
        
        if db_name not in self.config:
            raise ValueError(f"未找到数据库配置: {db_name}")
        
        db_config = self.config[db_name]
        connection_string = self._build_connection_string(db_config)
        
        engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=db_config.get('pool_size', 5),
            max_overflow=db_config.get('max_overflow', 10),
            pool_pre_ping=True,
            echo=False
        )
        
        self.engines[db_name] = engine
        logger.info(f"数据库引擎已创建: {db_name}")
        return engine
    
    def get_session(self, db_name: str) -> Session:
        """获取数据库会话"""
        if db_name not in self.session_makers:
            engine = self.get_engine(db_name)
            self.session_makers[db_name] = sessionmaker(bind=engine)
        
        return self.session_makers[db_name]()
    
    def test_connection(self, db_name: str) -> bool:
        """测试数据库连接"""
        try:
            engine = self.get_engine(db_name)
            db_config = self.config[db_name]
            db_type = db_config['type'].lower()
            
            # 根据数据库类型使用不同的测试SQL
            if db_type == 'oracle':
                test_sql = "SELECT 1 FROM DUAL"
            else:
                test_sql = "SELECT 1"
            
            with engine.connect() as conn:
                conn.execute(text(test_sql))
            logger.info(f"数据库连接测试成功: {db_name}")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败 {db_name}: {str(e)}")
            return False
    
    def execute_query(self, db_name: str, query: str, params: Optional[Dict] = None):
        """执行查询"""
        session = self.get_session(db_name)
        try:
            result = session.execute(text(query), params or {})
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"查询执行失败: {str(e)}")
            raise
        finally:
            session.close()
    
    def close_all(self):
        """关闭所有数据库连接"""
        for name, engine in self.engines.items():
            engine.dispose()
            logger.info(f"数据库连接已关闭: {name}")
