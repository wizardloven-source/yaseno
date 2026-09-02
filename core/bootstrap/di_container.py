# core/bootstrap/di_container.py
"""
Dependency Injection Container - YAseen ERP Enterprise Edition
حاوية حقن التبعيات المتكاملة لإدارة دورة حياة المكونات
"""

from typing import Dict, Any, Type, Callable, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class ServiceLifetime:
    """أنماط دورة حياة الخدمات"""
    SINGLETON = "singleton"      # نسخة واحدة طوال عمر التطبيق
    TRANSIENT = "transient"      # نسخة جديدة في كل مرة
    SCOPED = "scoped"            # نسخة واحدة لكل نطاق (مثل طلب HTTP)


class DependencyContainer:
    """
    حاوية حقن التبعيات الرئيسية
    
    الميزات:
    - تسجيل الخدمات بأنماط حياة مختلفة
    - دعم حقن التبعيات التلقائي
    - حل التبعيات الدائرية
    - تجميع لخدمات لتحميل بطيء (Lazy Loading)
    """
    
    def __init__(self):
        self._services: Dict[str, Dict] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped_instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._active_scopes: Dict[str, Any] = {}
        
    def register(
        self,
        name: str,
        service_type: Type,
        lifetime: str = ServiceLifetime.SINGLETON,
        dependencies: Optional[list] = None,
        factory: Optional[Callable] = None
    ) -> None:
        """
        تسجيل خدمة في الحاوية
        
        Args:
            name: اسم الخدمة
            service_type: نوع الخدمة (كلاس)
            lifetime: نمط دورة الحياة
            dependencies: قائمة بأسماء الخدمات المعتمدة
            factory: دالة مصنع مخصصة (اختياري)
        """
        self._services[name] = {
            "type": service_type,
            "lifetime": lifetime,
            "dependencies": dependencies or [],
            "factory": factory
        }
        logger.debug(f"Registered service: {name} (lifetime: {lifetime})")
    
    def register_instance(self, name: str, instance: Any) -> None:
        """تسجيل نسخة جاهزة من خدمة"""
        self._instances[name] = instance
        logger.debug(f"Registered instance: {name}")
    
    def resolve(self, name: str, scope: Optional[Dict] = None) -> Any:
        """
        حل الخدمة وإرجاع نسختها
        
        Args:
            name: اسم الخدمة
            scope: نطاق مخصص (للخدمات الـ Scoped)
        """
        if name in self._instances:
            return self._instances[name]
        
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered in container")
        
        service_info = self._services[name]
        lifetime = service_info["lifetime"]
        
        # Scoped services
        if lifetime == ServiceLifetime.SCOPED:
            if scope is None:
                raise ValueError(f"Scoped service '{name}' requires a scope")
            scope_key = id(scope)
            if scope_key not in self._scoped_instances:
                self._scoped_instances[scope_key] = {}
            if name not in self._scoped_instances[scope_key]:
                self._scoped_instances[scope_key][name] = self._create_instance(service_info, scope)
            return self._scoped_instances[scope_key][name]
        
        # Singleton services
        if lifetime == ServiceLifetime.SINGLETON:
            if name not in self._instances:
                self._instances[name] = self._create_instance(service_info)
            return self._instances[name]
        
        # Transient services
        return self._create_instance(service_info)
    
    def _create_instance(self, service_info: Dict, scope: Optional[Dict] = None) -> Any:
        """إنشاء نسخة جديدة من الخدمة مع حل تبعياتها"""
        service_type = service_info["type"]
        dependencies = service_info["dependencies"]
        
        # جمع التبعيات
        resolved_deps = []
        for dep_name in dependencies:
            resolved_deps.append(self.resolve(dep_name, scope))
        
        # استخدام المصنع المخصص إذا وجد
        if service_info["factory"]:
            return service_info["factory"](*resolved_deps)
        
        # إنشاء نسخة عادية
        return service_type(*resolved_deps)
    
    def create_scope(self) -> 'DependencyScope':
        """إنشاء نطاق جديد للخدمات الـ Scoped"""
        return DependencyScope(self)
    
    def clear_scoped(self) -> None:
        """مسح جميع الخدمات الـ Scoped"""
        self._scoped_instances.clear()
    
    def clear_all(self) -> None:
        """مسح جميع الخدمات"""
        self._instances.clear()
        self._scoped_instances.clear()
        self._active_scopes.clear()


class DependencyScope:
    """نطاق الخدمات (لـ HTTP requests, Unit of Work, etc)"""
    
    def __init__(self, container: DependencyContainer):
        self._container = container
        self._scope_id = id(self)
        self._services: Dict[str, Any] = {}
    
    def resolve(self, name: str) -> Any:
        """حل خدمة داخل النطاق"""
        if name in self._services:
            return self._services[name]
        
        service_info = self._container._services.get(name)
        if not service_info:
            raise KeyError(f"Service '{name}' not registered")
        
        instance = self._container._create_instance(service_info, self._services)
        self._services[name] = instance
        return instance
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._services.clear()


# حاوية عالمية واحدة
global_container = DependencyContainer()


def inject(*service_names):
    """
    Decorator لحقن الخدمات تلقائياً في الدوال والكلاسات
    
    الاستخدام:
        @inject("journal_repo", "ledger_engine")
        def my_handler(journal_repo, ledger_engine, user_id):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # جمع الخدمات المطلوبة
            services = {}
            for service_name in service_names:
                services[service_name] = global_container.resolve(service_name)
            
            # دمج الخدمات مع المعاملات الموجودة
            all_args = list(args)
            for service_name, service_instance in services.items():
                if service_name not in kwargs:
                    kwargs[service_name] = service_instance
            
            return func(*args, **kwargs)
        return wrapper
    return decorator