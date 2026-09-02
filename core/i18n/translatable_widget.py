# core/i18n/translatable_widget.py
"""
Base Class for All Translatable Widgets - YAseen ERP Enterprise Edition

كل نافذة في النظام ترث من هذه الفئة لضمان:
    1. الاشتراك التلقائي في تغيير اللغة.
    2. إعادة ترجمة الواجهة بشكل موحد.
    3. منع تكرار الكود (DRY).
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

from .translator import TranslationManager


class TranslatableWidget(QWidget):
    """
    الفئة الأساسية لجميع الواجهات القابلة للترجمة.
    
    كل واجهة ترث من هذه الفئة يجب أن تطبق دالة `retranslate_ui`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._translator = TranslationManager.instance()
        
        # اشتراك دائم في حدث تغيير اللغة
        self._translator.language_changed.connect(self._on_language_changed_handler)
        
        # ✅ لا تستدعي retranslate_ui هنا - سيتم استدعاؤها بعد بناء الواجهة
        # self.retranslate_ui()
        self._update_layout_direction()

    def showEvent(self, event):
        """استدعاء الترجمة عند أول ظهور للنافذة (بعد بناء الواجهة بالكامل)"""
        super().showEvent(event)
        self.retranslate_ui()
        self._update_layout_direction()

    def _on_language_changed_handler(self, lang_code: str):
        """معالج مركزي لتغيير اللغة."""
        self.retranslate_ui()
        self._update_layout_direction()

    def retranslate_ui(self):
        """
        يجب إعادة تعريف هذه الدالة في كل نافذة لترجمة عناصرها.
        لا تحتوي على أي منطق آخر.
        """
        pass

    def _update_layout_direction(self):
        """تحديث اتجاه التخطيط (RTL/LTR) بناءً على اللغة الحالية."""
        lang_info = self._translator.get_language_info()
        if lang_info.direction == "rtl":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)