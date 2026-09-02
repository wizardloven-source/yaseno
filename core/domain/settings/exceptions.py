# core/domain/settings/exceptions.py
"""Settings Domain Exceptions"""


class SettingsError(Exception):
    """استثناء أساسي للإعدادات"""
    pass


class SettingsNotFoundError(SettingsError):
    """الإعدادات غير موجودة"""
    def __init__(self):
        super().__init__("Settings not found. Run initialization first.")