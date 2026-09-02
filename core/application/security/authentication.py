# core/application/security/authentication.py
"""
Authentication Service - خدمة المصادقة
✅ محدث: دعم تشفير كلمات المرور عبر PasswordHasher
✅ محدث: دعم إدارة الجلسات
✅ محدث: دعم تتبع محاولات الدخول
"""

import uuid
import time
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from core.domain.auth.entities import User
from core.domain.auth.value_objects import UserId
from core.domain.auth.interfaces import IUserRepository
from core.shared.exceptions import AuthenticationError, ValidationError

# ✅ استيراد خدمة تشفير كلمات المرور
from core.application.security.password_hasher import PasswordHasher

import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """
    مدير الجلسات - يدير جلسات المستخدمين
    
    الميزات:
        1. إنشاء جلسات جديدة
        2. التحقق من صحة الجلسات
        3. انتهاء صلاحية الجلسات
        4. إلغاء الجلسات
    """
    
    def __init__(self, secret_key: str, session_timeout: int = 3600):
        """
        Args:
            secret_key: المفتاح السري لتوقيع الجلسات
            session_timeout: مدة صلاحية الجلسة بالثواني (افتراضي: 1 ساعة)
        """
        self._secret_key = secret_key
        self._session_timeout = session_timeout
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timestamps: Dict[str, float] = {}
    
    def create_session(self, data: Dict[str, Any]) -> str:
        """
        إنشاء جلسة جديدة
        
        Args:
            data: بيانات الجلسة (user_id, username, إلخ)
        
        Returns:
            str: معرف الجلسة
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = data
        self._session_timestamps[session_id] = time.time()
        
        logger.debug(f"Session created: {session_id[:8]}... for user {data.get('username')}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        الحصول على بيانات الجلسة
        
        Args:
            session_id: معرف الجلسة
        
        Returns:
            Optional[Dict]: بيانات الجلسة أو None إذا كانت غير صالحة
        """
        if session_id not in self._sessions:
            return None
        
        # التحقق من صلاحية الجلسة
        if self._is_session_expired(session_id):
            self.invalidate_session(session_id)
            return None
        
        # تحديث وقت آخر نشاط
        self._session_timestamps[session_id] = time.time()
        
        return self._sessions[session_id]
    
    def invalidate_session(self, session_id: str) -> None:
        """إلغاء الجلسة"""
        if session_id in self._sessions:
            user = self._sessions[session_id].get('username', 'unknown')
            del self._sessions[session_id]
            del self._session_timestamps[session_id]
            logger.debug(f"Session invalidated: {session_id[:8]}... for user {user}")
    
    def _is_session_expired(self, session_id: str) -> bool:
        """التحقق من انتهاء صلاحية الجلسة"""
        if session_id not in self._session_timestamps:
            return True
        
        elapsed = time.time() - self._session_timestamps[session_id]
        return elapsed > self._session_timeout
    
    def get_active_sessions(self) -> List[str]:
        """الحصول على قائمة معرفات الجلسات النشطة"""
        return list(self._sessions.keys())
    
    def get_session_count(self) -> int:
        """عدد الجلسات النشطة"""
        return len(self._sessions)


class LoginAttemptTracker:
    """
    متتبع محاولات الدخول - يمنع هجمات القوة العمياء (Brute Force)
    
    الميزات:
        1. تتبع المحاولات الفاشلة لكل IP
        2. قفل IP بعد عدد معين من المحاولات
        3. إعادة تعيين المحاولات بعد وقت محدد
    """
    
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15):
        """
        Args:
            max_attempts: الحد الأقصى للمحاولات الفاشلة
            lockout_minutes: مدة القفل بالدقائق
        """
        self._max_attempts = max_attempts
        self._lockout_minutes = lockout_minutes
        self._attempts: Dict[str, List[float]] = {}  # IP -> قائمة بأوقات المحاولات
        self._locked_until: Dict[str, float] = {}    # IP -> وقت انتهاء القفل
    
    def record_failed_attempt(self, ip_address: str) -> None:
        """تسجيل محاولة فاشلة"""
        now = time.time()
        
        if ip_address not in self._attempts:
            self._attempts[ip_address] = []
        
        # إزالة المحاولات القديمة (أكثر من ساعة)
        self._attempts[ip_address] = [
            t for t in self._attempts[ip_address]
            if now - t < 3600
        ]
        
        self._attempts[ip_address].append(now)
        
        # التحقق من تجاوز الحد
        if len(self._attempts[ip_address]) >= self._max_attempts:
            self._locked_until[ip_address] = now + (self._lockout_minutes * 60)
            logger.warning(f"IP {ip_address} locked out for {self._lockout_minutes} minutes")
    
    def is_locked_out(self, ip_address: str) -> bool:
        """التحقق من أن IP مقفل"""
        if ip_address not in self._locked_until:
            return False
        
        if time.time() < self._locked_until[ip_address]:
            return True
        
        # انتهت مدة القفل
        del self._locked_until[ip_address]
        self._attempts.pop(ip_address, None)
        return False
    
    def reset_attempts(self, ip_address: str) -> None:
        """إعادة تعيين محاولات IP"""
        self._attempts.pop(ip_address, None)
        self._locked_until.pop(ip_address, None)
    
    def get_remaining_lockout_time(self, ip_address: str) -> int:
        """الحصول على الوقت المتبقي من القفل بالثواني"""
        if ip_address not in self._locked_until:
            return 0
        
        remaining = self._locked_until[ip_address] - time.time()
        return max(0, int(remaining))


class AuthenticationService:
    """
    خدمة المصادقة - تدير تسجيل الدخول والجلسات
    
    الميزات:
        1. مصادقة المستخدمين باستخدام اسم المستخدم وكلمة المرور
        2. التحقق من حالة المستخدم (نشط/غير نشط)
        3. تحديث وقت آخر تسجيل دخول
        4. تغيير كلمة المرور
        5. إعادة تعيين كلمة المرور
    """
    
    def __init__(self, user_repository: IUserRepository):
        """
        Args:
            user_repository: مستودع المستخدمين
        """
        self._user_repo = user_repository
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        مصادقة المستخدم
        
        Args:
            username: اسم المستخدم
            password: كلمة المرور (نص عادي)
        
        Returns:
            Optional[User]: كائن المستخدم إذا نجحت المصادقة، وإلا None
        
        Raises:
            AuthenticationError: إذا فشلت المصادقة
        """
        # ✅ جلب المستخدم
        user = self._user_repo.get_by_username(username)
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        # ✅ التحقق من كلمة المرور باستخدام bcrypt
        if not PasswordHasher.verify(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
            return None
        
        # ✅ التحقق من أن المستخدم نشط
        if not user.is_active:
            logger.warning(f"Authentication failed: user '{username}' is inactive")
            return None
        
        # ✅ تحديث وقت آخر تسجيل دخول
        user.last_login = datetime.now(timezone.utc)
        self._user_repo.save(user)
        
        logger.info(f"User '{username}' authenticated successfully")
        return user
    
    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
        confirm_password: Optional[str] = None
    ) -> bool:
        """
        تغيير كلمة مرور المستخدم
        
        Args:
            user_id: معرف المستخدم
            old_password: كلمة المرور القديمة
            new_password: كلمة المرور الجديدة
            confirm_password: تأكيد كلمة المرور (اختياري)
        
        Returns:
            bool: True إذا تم التغيير بنجاح
        
        Raises:
            ValidationError: إذا فشل التحقق من صحة كلمة المرور
        """
        # جلب المستخدم
        user = self._user_repo.get_by_id(UserId.from_string(user_id))
        if not user:
            raise ValidationError(f"User '{user_id}' not found")
        
        # ✅ التحقق من كلمة المرور القديمة
        if not PasswordHasher.verify(old_password, user.password_hash):
            raise ValidationError("Invalid current password")
        
        # ✅ التحقق من تطابق كلمة المرور الجديدة مع التأكيد
        if confirm_password and new_password != confirm_password:
            raise ValidationError("Passwords do not match")
        
        # ✅ التحقق من قوة كلمة المرور الجديدة
        is_valid, error = self.validate_password_strength(new_password)
        if not is_valid:
            raise ValidationError(error)
        
        # ✅ تشفير كلمة المرور الجديدة
        user.password_hash = PasswordHasher.hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        user.version += 1
        
        self._user_repo.save(user)
        logger.info(f"Password changed for user '{user.username}'")
        return True
    
    def reset_password(self, user_id: str, new_password: str) -> bool:
        """
        إعادة تعيين كلمة مرور المستخدم (للمديرين فقط)
        
        Args:
            user_id: معرف المستخدم
            new_password: كلمة المرور الجديدة
        
        Returns:
            bool: True إذا تم التغيير بنجاح
        
        Raises:
            ValidationError: إذا فشل التحقق من صحة كلمة المرور
        """
        # جلب المستخدم
        user = self._user_repo.get_by_id(UserId.from_string(user_id))
        if not user:
            raise ValidationError(f"User '{user_id}' not found")
        
        # ✅ التحقق من قوة كلمة المرور
        is_valid, error = self.validate_password_strength(new_password)
        if not is_valid:
            raise ValidationError(error)
        
        # ✅ تشفير كلمة المرور الجديدة
        user.password_hash = PasswordHasher.hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        user.version += 1
        
        self._user_repo.save(user)
        logger.info(f"Password reset for user '{user.username}'")
        return True
    
    def validate_password_strength(self, password: str) -> tuple[bool, Optional[str]]:
        """
        التحقق من قوة كلمة المرور
        
        Args:
            password: كلمة المرور المراد التحقق منها
        
        Returns:
            tuple[bool, Optional[str]]: (صالح, رسالة الخطأ)
        """
        if len(password) < PasswordHasher.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {PasswordHasher.MIN_PASSWORD_LENGTH} characters"
        
        # ✅ التحقق من وجود حرف كبير
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        # ✅ التحقق من وجود حرف صغير
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        # ✅ التحقق من وجود رقم
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        # ✅ التحقق من وجود حرف خاص
        special_chars = "!@#$%^&*()_+-=[]{};':\"\\|,.<>/?`~"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        return True, None


# =============================================================================
# دالة مساعدة لتوليد كلمة مرور عشوائية
# =============================================================================

def generate_random_password(length: int = 12) -> str:
    """
    توليد كلمة مرور عشوائية قوية
    
    Args:
        length: طول كلمة المرور
        
    Returns:
        str: كلمة مرور عشوائية
    """
    import random
    import string
    
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}"
    
    # ضمان وجود حرف كبير، حرف صغير، رقم، وحرف خاص
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*()_+-=[]{}"),
    ]
    
    # إضافة أحرف عشوائية
    password.extend(random.choice(chars) for _ in range(length - 4))
    
    # خلط الكلمة
    random.shuffle(password)
    
    return ''.join(password)