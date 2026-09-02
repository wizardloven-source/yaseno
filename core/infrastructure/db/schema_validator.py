"""
Schema Validator - التحقق من صحة مخطط قاعدة البيانات
"""

import logging
from typing import Dict, Any, List, Tuple
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from core.infrastructure.db.models.account_model import Base

logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    مدقق مخطط قاعدة البيانات
    يتحقق من تطابق المخطط مع تعريف SQLAlchemy
    """
    
    def __init__(self, engine: Engine):
        self._engine = engine
    
    def validate(self) -> Dict[str, Any]:
        """
        التحقق من صحة المخطط بالكامل
        
        Returns:
            Dict: تقرير التحقق
        """
        report = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_tables": [],
            "missing_columns": {},
            "missing_indexes": {},
            "missing_constraints": {}
        }
        
        inspector = inspect(self._engine)
        existing_tables = set(inspector.get_table_names())
        
        for table_name, table in Base.metadata.tables.items():
            # التحقق من وجود الجدول
            if table_name not in existing_tables:
                report["missing_tables"].append(table_name)
                report["is_valid"] = False
                continue
            
            # التحقق من الأعمدة
            existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
            required_cols = {col.name for col in table.columns}
            missing = required_cols - existing_cols
            
            if missing:
                report["missing_columns"][table_name] = list(missing)
                report["is_valid"] = False
            
            # التحقق من أنواع الأعمدة
            for col in inspector.get_columns(table_name):
                if col['name'] in table.columns:
                    required_col = table.columns[col['name']]
                    if not self._check_column_type(col, required_col):
                        report["warnings"].append(
                            f"Column {table_name}.{col['name']} type mismatch"
                        )
            
            # التحقق من الفهارس
            try:
                existing_idx = {idx['name'] for idx in inspector.get_indexes(table_name)}
                required_idx = {idx.name for idx in table.indexes if idx.name}
                missing_idx = required_idx - existing_idx
                
                if missing_idx:
                    report["missing_indexes"][table_name] = list(missing_idx)
                    report["warnings"].append(
                        f"Missing indexes on {table_name}: {missing_idx}"
                    )
            except Exception:
                pass
        
        return report
    
    def _check_column_type(self, actual: Dict, required) -> bool:
        """التحقق من تطابق نوع العمود"""
        # يمكن توسيع هذا للتحقق من الأنواع المختلفة
        return True  # مبسط حالياً


def validate_database_schema(bootstrap) -> Dict[str, Any]:
    """التحقق من صحة مخطط قاعدة البيانات"""
    validator = SchemaValidator(bootstrap.session_factory.engine)
    return validator.validate()