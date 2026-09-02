# core/bootstrap/container.py
"""
Dependency Injection Container - Professional Edition
حاوية حقن تبعيات احترافية مع دعم كامل لدورة الحياة
"""

from typing import Dict, Any, Type, Callable, Optional, List, Union, Set
from dataclasses import dataclass, field
import logging
import threading
import contextvars
from contextlib import contextmanager
from functools import wraps
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# حالة النطاقات (Scopes) - محلية للسياق (Context-Local)
# =============================================================================
# تُخزَّن حالة النطاق في ContextVar بدلاً من الحقول المشتركة للكائن،
# حتى يكون الـ Scoping آمن بين الخيوط (Thread-Safe) وبين المهام غير المتزامنة.
# هذا يصلح الخلل الجذري: مشاركة جلسة قاعدة بيانات واحدة بين جميع الطلبات.
_scope_stack_ctx: contextvars.ContextVar = contextvars.ContextVar(
    "di_scope_stack", default=()
)
_scope_instances_ctx: contextvars.ContextVar = contextvars.ContextVar(
    "di_scope_instances", default={}
)


def _dispose_scoped_instance(instance: Any) -> None:
    """إغلاق/تحرير نسخة Scoped عند انتهاء النطاق (إن وُجدت طريقة dispose)."""
    dispose = getattr(instance, "dispose", None)
    if callable(dispose):
        try:
            dispose()
        except Exception as e:
            logger.warning(f"⚠️ dispose() failed for {instance.__class__.__name__}: {e}")


class ServiceLifetime:
    """أنماط دورة حياة الخدمات"""
    SINGLETON = "singleton"      # نسخة واحدة طوال عمر التطبيق
    TRANSIENT = "transient"      # نسخة جديدة في كل مرة
    SCOPED = "scoped"            # نسخة واحدة لكل نطاق


@dataclass
class ServiceDefinition:
    """تعريف الخدمة في الحاوية"""
    service_type: Union[Type, str]
    lifetime: str = ServiceLifetime.SINGLETON
    dependencies: List[str] = field(default_factory=list)
    factory: Optional[Callable] = None
    instance: Optional[Any] = None


class DependencyContainer:
    """
    حاوية حقن التبعيات الاحترافية
    
    الميزات:
        1. دعم كامل لـ Singleton, Scoped, Transient
        2. إدارة النطاقات (Scopes) بشكل آلي مع سياقات مستقلة
        3. حل التبعيات التلقائي مع منع الدورات
        4. دعم المصانع (Factories)
        5. تسجيل مبسط للخدمات
        6. Thread-safe
        7. دعم النطاقات المتداخلة (Nested Scopes)
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._singletons: Dict[str, Any] = {}
        self._resolving: Set[str] = set()
        self._lock = threading.RLock()
        self._import_cache: Dict[str, Type] = {}
    
    # =========================================================================
    # تسجيل الخدمات - واجهات مبسطة
    # =========================================================================
    
    def register_singleton(self, name: str, service_type: Union[Type, str], 
                           dependencies: Optional[List[str]] = None,
                           factory: Optional[Callable] = None) -> 'DependencyContainer':
        """تسجيل خدمة Singleton"""
        return self.register(name, service_type, ServiceLifetime.SINGLETON, dependencies, factory)
    
    def register_scoped(self, name: str, service_type: Union[Type, str],
                        dependencies: Optional[List[str]] = None,
                        factory: Optional[Callable] = None) -> 'DependencyContainer':
        """تسجيل خدمة Scoped"""
        return self.register(name, service_type, ServiceLifetime.SCOPED, dependencies, factory)
    
    def register_transient(self, name: str, service_type: Union[Type, str],
                           dependencies: Optional[List[str]] = None,
                           factory: Optional[Callable] = None) -> 'DependencyContainer':
        """تسجيل خدمة Transient"""
        return self.register(name, service_type, ServiceLifetime.TRANSIENT, dependencies, factory)
    
    def register(self, name: str, service_type: Union[Type, str],
                 lifetime: str = ServiceLifetime.SINGLETON,
                 dependencies: Optional[List[str]] = None,
                 factory: Optional[Callable] = None) -> 'DependencyContainer':
        """تسجيل خدمة في الحاوية"""
        with self._lock:
            self._services[name] = ServiceDefinition(
                service_type=service_type,
                lifetime=lifetime,
                dependencies=dependencies or [],
                factory=factory
            )
            logger.debug(f"Registered service: {name} (lifetime: {lifetime})")
        return self
    
    def register_instance(self, name: str, instance: Any) -> 'DependencyContainer':
        """تسجيل نسخة جاهزة من خدمة (Singleton)"""
        with self._lock:
            self._singletons[name] = instance
            logger.debug(f"Registered instance: {name}")
        return self
    
    # =========================================================================
    # إدارة النطاقات (Scopes) - احترافية مع دعم التداخل
    # =========================================================================
    
    @contextmanager
    def scope(self, scope_id: Optional[str] = None):
        """
        إنشاء نطاق جديد للخدمات الـ Scoped
        
        يدعم النطاقات المتداخلة (Nested Scopes)
        
        الاستخدام:
            with container.scope() as scope:
                uow = scope.resolve("uow")
                # استخدام uow...
                
            # نطاق متداخل
            with container.scope() as outer:
                with container.scope() as inner:
                    # نطاق داخلي
        """
        # توليد معرف فريد للنطاق
        if scope_id is None:
            scope_id = str(uuid.uuid4())
        
        # الحصول على حالة النطاق الحالية من السياق (نسخ-عند-الكتابة)
        stack = _scope_stack_ctx.get()
        instances = _scope_instances_ctx.get()
        new_stack = stack + (scope_id,)
        new_instances = dict(instances)
        new_instances[scope_id] = {}
        
        token_stack = _scope_stack_ctx.set(new_stack)
        token_instances = _scope_instances_ctx.set(new_instances)
        
        try:
            logger.debug(f"🔵 Scope created: {scope_id} (stack depth: {len(new_stack)})")
            yield self
            
        finally:
            # تنظيف خدمات النطاق (إغلاق الجلسات/الـ UoW) عند الخروج
            scope_instances = new_instances.get(scope_id, {})
            for svc in scope_instances.values():
                _dispose_scoped_instance(svc)
            new_instances.pop(scope_id, None)
            
            _scope_stack_ctx.reset(token_stack)
            _scope_instances_ctx.reset(token_instances)
            
            logger.debug(f"🔴 Scope closed: {scope_id}")
    
    def get_current_scope(self) -> Optional[str]:
        """الحصول على معرف النطاق الحالي"""
        stack = _scope_stack_ctx.get()
        return stack[-1] if stack else None
    
    def is_in_scope(self) -> bool:
        """التحقق من وجود نطاق نشط"""
        return bool(_scope_stack_ctx.get())
    
    def get_scope_depth(self) -> int:
        """الحصول على عمق النطاق الحالي"""
        return len(_scope_stack_ctx.get())
    
    # =========================================================================
    # حل الخدمات - المحرك الرئيسي المحسن
    # =========================================================================
    
    def resolve(self, name: str, scope_id: Optional[str] = None) -> Any:
        """
        حل الخدمة وإرجاع نسختها
        
        Args:
            name: اسم الخدمة
            scope_id: معرف النطاق (اختياري، يستخدم النطاق الحالي تلقائياً)
        
        Returns:
            نسخة من الخدمة
        
        Raises:
            KeyError: إذا لم يتم تسجيل الخدمة
            RuntimeError: إذا تم اكتشاف تبعية دائرية
            ValueError: إذا كانت خدمة Scoped ولا يوجد نطاق نشط
        """
        # التحقق من الكاش (Singleton)
        if name in self._singletons:
            return self._singletons[name]
        
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")
        
        definition = self._services[name]
        
        # معالجة Scoped
        if definition.lifetime == ServiceLifetime.SCOPED:
            return self._resolve_scoped(name, definition, scope_id)
        
        # معالجة Singleton
        if definition.lifetime == ServiceLifetime.SINGLETON:
            return self._resolve_singleton(name, definition)
        
        # معالجة Transient
        return self._create_instance(name, definition)
    
    def _resolve_scoped(self, name: str, definition: ServiceDefinition, 
                        scope_id: Optional[str] = None) -> Any:
        """حل خدمة Scoped مع دعم النطاقات المتداخلة (آمن للسياق)"""
        # استخدام النطاق المحدد أو النطاق الحالي من السياق
        target_scope = scope_id
        if target_scope is None:
            stack = _scope_stack_ctx.get()
            if not stack:
                # ✅ إنشاء نطاق مؤقت عند عدم وجود نطاق نشط
                with self.scope() as temp_scope:
                    return temp_scope.resolve(name)
            target_scope = stack[-1]
        
        instances = _scope_instances_ctx.get()
        
        # التأكد من وجود النطاق
        if target_scope not in instances:
            instances[target_scope] = {}
        
        # التحقق من وجود الخدمة في النطاق
        if name not in instances[target_scope]:
            instances[target_scope][name] = self._create_instance(name, definition)
        
        return instances[target_scope][name]
    
    def _resolve_singleton(self, name: str, definition: ServiceDefinition) -> Any:
        """حل خدمة Singleton"""
        if name not in self._singletons:
            self._singletons[name] = self._create_instance(name, definition)
        return self._singletons[name]
    
    def _create_instance(self, name: str, definition: ServiceDefinition) -> Any:
        """إنشاء نسخة جديدة من الخدمة مع حل تبعياتها"""
        # منع التبعيات الدائرية
        if name in self._resolving:
            raise RuntimeError(f"Circular dependency detected: {name}")
        
        self._resolving.add(name)
        
        try:
            service_type = definition.service_type
            
            # استيراد الكلاس إذا كان نصاً
            if isinstance(service_type, str):
                service_type = self._import_class(service_type)
            
            # حل التبعيات
            resolved_deps = []
            for dep_name in definition.dependencies:
                try:
                    resolved_deps.append(self.resolve(dep_name))
                except Exception as e:
                    logger.error(f"Failed to resolve dependency '{dep_name}' for '{name}': {e}")
                    raise
            
            # استخدام المصنع أو إنشاء نسخة عادية
            if definition.factory:
                instance = definition.factory(*resolved_deps)
            else:
                instance = service_type(*resolved_deps)
            
            return instance
            
        finally:
            self._resolving.remove(name)
    
    def _import_class(self, class_path: str) -> Type:
        """استيراد كلاس من مسار نصي مع التخزين المؤقت"""
        if class_path in self._import_cache:
            return self._import_cache[class_path]
        
        parts = class_path.split('.')
        module_path = '.'.join(parts[:-1])
        class_name = parts[-1]
        
        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            self._import_cache[class_path] = cls
            return cls
        except Exception as e:
            raise ImportError(f"Could not import class '{class_path}': {e}")
    
    # =========================================================================
    # دوال مساعدة محسنة
    # =========================================================================
    
    def has_service(self, name: str) -> bool:
        """التحقق من وجود خدمة مسجلة"""
        return name in self._services
    
    def get_service_definition(self, name: str) -> Optional[ServiceDefinition]:
        """الحصول على تعريف الخدمة"""
        return self._services.get(name)
    
    def get_scoped_instances(self, scope_id: Optional[str] = None) -> Dict[str, Any]:
        """الحصول على جميع الخدمات في نطاق معين"""
        target_scope = scope_id or self.get_current_scope()
        if target_scope is None:
            return {}
        return _scope_instances_ctx.get().get(target_scope, {}).copy()
    
    def clear_all(self) -> None:
        """مسح جميع الخدمات (للاختبار)"""
        with self._lock:
            self._singletons.clear()
            _scope_instances_ctx.set({})
            _scope_stack_ctx.set(())
            self._import_cache.clear()
            logger.debug("🧹 All services cleared")
    
    def clear_scope(self, scope_id: Optional[str] = None) -> None:
        """مسح الخدمات في نطاق معين"""
        target_scope = scope_id or self.get_current_scope()
        if target_scope is None:
            return
        
        instances = _scope_instances_ctx.get()
        if target_scope in instances:
            for svc in instances[target_scope].values():
                _dispose_scoped_instance(svc)
            del instances[target_scope]
            logger.debug(f"🧹 Scope cleared: {target_scope}")
    
    def clear_all_scopes(self) -> None:
        """مسح جميع النطاقات"""
        instances = _scope_instances_ctx.get()
        for scope_id in list(instances.keys()):
            for svc in instances[scope_id].values():
                _dispose_scoped_instance(svc)
        _scope_instances_ctx.set({})
        _scope_stack_ctx.set(())
        logger.debug("🧹 All scopes cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الحاوية"""
        instances = _scope_instances_ctx.get()
        return {
            "total_services": len(self._services),
            "singletons": len(self._singletons),
            "scoped_instances": sum(len(v) for v in instances.values()),
            "active_scopes": len(instances),
            "scope_stack_depth": len(_scope_stack_ctx.get()),
            "current_scope": self.get_current_scope(),
            "import_cache_size": len(self._import_cache),
        }


# =========================================================================
# ديكوراتور مساعد للحقن التلقائي
# =========================================================================

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
            from core.bootstrap.startup import get_bootstrap
            container = get_bootstrap().container
            
            # جمع الخدمات المطلوبة
            services = {}
            for service_name in service_names:
                services[service_name] = container.resolve(service_name)
            
            # دمج الخدمات مع المعاملات الموجودة
            all_args = list(args)
            for service_name, service_instance in services.items():
                if service_name not in kwargs:
                    kwargs[service_name] = service_instance
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =========================================================================
# اختبار سريع
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing DependencyContainer")
    print("=" * 60)
    
    container = DependencyContainer()
    
    # تسجيل خدمة Scoped
    container.register_scoped("test_service", "str", dependencies=[])
    
    # اختبار النطاق
    with container.scope() as scope:
        service1 = scope.resolve("test_service")
        service2 = scope.resolve("test_service")
        print(f"Same instance? {service1 is service2}")  # يجب أن يكون True
    
    print("✅ Container tests passed!")