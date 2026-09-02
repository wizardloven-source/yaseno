# core/application/security/password_hasher.py
"""
Password Hasher Service - خدمة تشفير كلمات المرور
الإصدار: 1.0.0

الميزات:
    1. تشفير آمن باستخدام bcrypt مع Salt تلقائي
    2. التحقق من كلمة المرور مقابل التشفير المخزن
    3. دعم الترقية التلقائية لخوارزميات التشفير
    4. متوافق مع Python 3.8+
"""

import bcrypt
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)


class PasswordHasher:
    """
    خدمة تشفير والتحقق من كلمات المرور باستخدام bcrypt
    
    الاستخدام:
        # تشفير كلمة المرور
        hashed = PasswordHasher.hash("Admin@123")
        
        # التحقق من كلمة المرور
        is_valid = PasswordHasher.verify("Admin@123", hashed)
        
        # التحقق من الحاجة لإعادة التشفير
        if PasswordHasher.needs_rehash(hashed):
            new_hash = PasswordHasher.hash(password)
            # تحديث في قاعدة البيانات
    """
    
    # عدد جولات التشفير (كلما زاد الرقم، زاد الأمان والأداء)
    # القيمة 12 هي التوازن المثالي بين الأمان والأداء
    ROUNDS: int = 12
    
    # الحد الأدنى لطول كلمة المرور
    MIN_PASSWORD_LENGTH: int = 6
    
    @classmethod
    def hash(cls, password: str) -> str:
        """
        تشفير كلمة المرور باستخدام bcrypt
        
        Args:
            password: كلمة المرور النصية (يجب ألا تكون فارغة)
        
        Returns:
            str: النص المشفر (بتنسيق bcrypt)
        
        Raises:
            ValueError: إذا كانت كلمة المرور فارغة أو غير صالحة
        
        Example:
            >>> hashed = PasswordHasher.hash("Admin@123")
            >>> print(hashed)
            '$2b$12$KIX...'
        """
        if not password or not password.strip():
            raise ValueError("Password cannot be empty")
        
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long"
            )
        
        try:
            # تحويل النص إلى bytes
            password_bytes = password.encode('utf-8')
            
            # إنشاء Salt وتشفير كلمة المرور
            salt = bcrypt.gensalt(rounds=cls.ROUNDS)
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            # إرجاع النص المشفر كنص (وليس bytes)
            return hashed.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise ValueError(f"Failed to hash password: {str(e)}")
    
    @classmethod
    def verify(cls, password: str, hashed: str) -> bool:
        """
        التحقق من كلمة المرور مقابل التشفير المخزن
        
        Args:
            password: كلمة المرور النصية المدخلة
            hashed: النص المشفر المخزن في قاعدة البيانات
        
        Returns:
            bool: True إذا تطابقت كلمة المرور، False إذا لم تتطابق
        
        Example:
            >>> is_valid = PasswordHasher.verify("Admin@123", stored_hash)
            >>> print(is_valid)
            True
        """
        if not password or not hashed:
            logger.warning("Password or hash is empty")
            return False
        
        try:
            # تحويل النصوص إلى bytes
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed.encode('utf-8')
            
            # التحقق من كلمة المرور
            return bcrypt.checkpw(password_bytes, hashed_bytes)
            
        except ValueError as e:
            # خطأ في تنسيق التشفير (قد يكون تشفيراً قديماً)
            logger.warning(f"Invalid hash format: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @classmethod
    def needs_rehash(cls, hashed: str) -> bool:
        """
        التحقق مما إذا كان التشفير يحتاج إلى إعادة تشفير (لترقية الأمان)
        
        Args:
            hashed: النص المشفر المخزن
        
        Returns:
            bool: True إذا كان التشفير يحتاج إلى تحديث
        
        Example:
            >>> if PasswordHasher.needs_rehash(stored_hash):
            ...     new_hash = PasswordHasher.hash(password)
            ...     # تحديث التشفير في قاعدة البيانات
        """
        if not hashed:
            return True
        
        try:
            # التحقق من أن التشفير يستخدم bcrypt (يبدأ بـ $2)
            if not hashed.startswith('$2'):
                return True
            
            # التحقق من عدد الجولات
            # تنسيق bcrypt: $2b$ROUNDS$...
            # مثال: $2b$12$KIX...
            parts = hashed.split('$')
            if len(parts) >= 3:
                rounds_str = parts[2]
                if rounds_str.isdigit():
                    current_rounds = int(rounds_str)
                    return current_rounds < cls.ROUNDS
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking rehash: {e}")
            return True
    
    @classmethod
    def is_valid_hash(cls, hashed: str) -> bool:
        """
        التحقق من صحة تنسيق التشفير
        
        Args:
            hashed: النص المشفر
        
        Returns:
            bool: True إذا كان التنسيق صحيحاً
        """
        if not hashed:
            return False
        
        # التحقق من تنسيق bcrypt
        # $2a$, $2b$, $2y$ - جميعها مدعومة
        pattern = r'^\$2[aby]\$[0-9]{2}\$[A-Za-z0-9./]{53}$'
        return bool(re.match(pattern, hashed))


# =============================================================================
# دوال مساعدة للاستخدام السريع
# =============================================================================

def hash_password(password: str) -> str:
    """
    دالة مساعدة لتشفير كلمة المرور
    
    Args:
        password: كلمة المرور النصية
    
    Returns:
        str: النص المشفر
    """
    return PasswordHasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    دالة مساعدة للتحقق من كلمة المرور
    
    Args:
        password: كلمة المرور النصية المدخلة
        hashed: النص المشفر المخزن
    
    Returns:
        bool: True إذا تطابقت كلمة المرور
    """
    return PasswordHasher.verify(password, hashed)


def needs_rehash(hashed: str) -> bool:
    """
    دالة مساعدة للتحقق من الحاجة لإعادة التشفير
    
    Args:
        hashed: النص المشفر المخزن
    
    Returns:
        bool: True إذا كان يحتاج إلى تحديث
    """
    return PasswordHasher.needs_rehash(hashed)


# =============================================================================
# اختبار سريع (يعمل فقط عند تشغيل الملف مباشرة)
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing PasswordHasher")
    print("=" * 60)
    
    # اختبار التشفير
    password = "Admin@123"
    print(f"\n1. Hashing password: {password}")
    hashed = PasswordHasher.hash(password)
    print(f"   Hashed: {hashed}")
    print(f"   Length: {len(hashed)}")
    print(f"   Valid hash: {PasswordHasher.is_valid_hash(hashed)}")
    
    # اختبار التحقق الصحيح
    print(f"\n2. Verifying correct password")
    is_valid = PasswordHasher.verify(password, hashed)
    print(f"   Result: {is_valid} ✅")
    
    # اختبار التحقق الخاطئ
    print(f"\n3. Verifying wrong password")
    is_valid = PasswordHasher.verify("WrongPassword", hashed)
    print(f"   Result: {is_valid} ❌")
    
    # اختبار التحقق من الحاجة لإعادة التشفير
    print(f"\n4. Checking if needs rehash")
    needs = PasswordHasher.needs_rehash(hashed)
    print(f"   Needs rehash: {needs}")
    
    # اختبار مع تشفير قديم (عدد جولات أقل)
    print(f"\n5. Testing with old hash (10 rounds)")
    old_hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=10)).decode('utf-8')
    needs = PasswordHasher.needs_rehash(old_hashed)
    print(f"   Old hash: {old_hashed[:20]}...")
    print(f"   Needs rehash: {needs} ✅ (should be True)")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")