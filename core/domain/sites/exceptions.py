# core/domain/sites/exceptions.py
"""
Domain Exceptions for Sites Context
استثناءات مجال المواقع - تعبر عن انتهاكات قواعد العمل
"""


class SiteError(Exception):
    """الاستثناء الأساسي لجميع أخطاء المواقع"""
    pass


class SiteNotFoundError(SiteError):
    """يُرفع عندما لا يتم العثور على الموقع"""
    def __init__(self, site_id: str):
        self.site_id = site_id
        super().__init__(f"Site not found: {site_id}")


class DuplicateSiteCodeError(SiteError):
    """يُرفع عند محاولة إنشاء موقع بكود مكرر"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Site code already exists: {code}")


class InvalidSiteCodeError(SiteError):
    """يُرفع عند استخدام كود موقع غير صالح"""
    def __init__(self, code: str, reason: str = ""):
        self.code = code
        super().__init__(f"Invalid site code '{code}': {reason}" if reason else f"Invalid site code: {code}")


class InvalidSiteTypeError(SiteError):
    """يُرفع عند استخدام نوع موقع غير صالح"""
    def __init__(self, site_type: str):
        self.site_type = site_type
        super().__init__(f"Invalid site type: {site_type}")


class CannotDeleteSiteWithReferencesError(SiteError):
    """يُرفع عند محاولة حذف موقع مرتبط بكيانات أخرى"""
    def __init__(self, site_code: str, reference_count: int):
        self.site_code = site_code
        self.reference_count = reference_count
        super().__init__(
            f"Cannot delete site '{site_code}' because it has {reference_count} references in the system"
        )


class ConcurrentModificationError(SiteError):
    """
    يُرفع عند فشل القفل التفاؤلي (تعديل متزامن من مستخدمين مختلفين)
    """
    def __init__(
        self,
        aggregate_type: str,
        aggregate_id: str,
        expected_version: int,
        actual_version: int
    ):
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"{aggregate_type} {aggregate_id} was modified concurrently. "
            f"Expected version {expected_version}, but database has version {actual_version}"
        )