# core/application/handlers/notifications/test_sound_handler.py
"""
Test Sound Handler - معالج اختبار الصوت
"""

import logging

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class TestSoundHandler(BaseHandler):
    """
    معالج اختبار الصوت
    """

    def __init__(self, sound_service):
        self._sound_service = sound_service

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ اختبار الصوت
        
        Args:
            command: أمر اختبار الصوت
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة الاختبار
        """
        logger.info("Testing notification sound")

        try:
            self._sound_service.play_test_sound(
                sound_type=command.sound_type or "default"
            )

            return {
                "success": True,
                "message": "Test sound played successfully",
                "sound_type": command.sound_type or "default"
            }
        except Exception as e:
            logger.error(f"Test sound failed: {e}")
            return {
                "success": False,
                "message": f"Test sound failed: {str(e)}"
            }