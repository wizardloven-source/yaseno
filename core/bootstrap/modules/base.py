# core/bootstrap/modules/base.py
"""
الوحدة الأساسية - كل وحدة تسجل خدماتها بنفسها
"""

from typing import TYPE_CHECKING, List, Dict, Any, Optional, Callable

if TYPE_CHECKING:
    from ..container import DependencyContainer


def lazy_event_handler(
    container: 'DependencyContainer',
    handler_name: str
) -> Callable[[Any], Any]:
    """
    إنشاء معالج أحداث يُحل في نطاق جديد (جلسة جديدة) لكل حدث.

    هذا يمنع مشاركة جلسة قاعدة بيانات واحدة بين جميع الأحداث/الطلبات.

    Args:
        container: الحاوية الجذرية (لإنشاء نطاق جديد لكل استدعاء)
        handler_name: اسم خدمة المعالج في الحاوية

    Returns:
        دالة تستقبل الحدث وتُسلمه لنسخة معالجة جديدة
    """
    def handle(event: Any) -> Any:
        with container.scope() as scoped:
            handler = scoped.resolve(handler_name)
            return handler(event)
    return handle


class Module:
    """
    الوحدة الأساسية - كل وحدة ترث منها وتسجل خدماتها
    
    الميزات:
        1. تسجيل Repositories
        2. تسجيل Services
        3. تسجيل Handlers
        4. تكوين Command/Query Buses
        5. إدارة التبعيات بين الوحدات
    """
    
    name: str = "base"
    description: str = "الوحدة الأساسية"
    dependencies: List[str] = []
    version: str = "1.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """
        تسجيل خدمات الوحدة في الحاوية
        
        Args:
            container: حاوية حقن التبعيات
        """
        pass
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """
        تكوين إضافي للوحدة بعد تسجيل الخدمات
        
        Args:
            container: حاوية حقن التبعيات
            config: إعدادات التطبيق
        """
        pass
    
    def get_dependencies(self) -> List[str]:
        """الحصول على قائمة تبعيات الوحدة"""
        return self.dependencies
    
    def is_dependency_satisfied(self, registered_modules: List[str]) -> bool:
        """التحقق من أن جميع التبعيات مسجلة"""
        return all(dep in registered_modules for dep in self.dependencies)