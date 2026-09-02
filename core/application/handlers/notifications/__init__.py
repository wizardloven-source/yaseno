# core/application/handlers/notifications/__init__.py
"""
Notifications Handlers - معالجات الإشعارات
"""

# ========== Command Handlers ==========
from .send_notification_handler import SendNotificationHandler
from .send_bulk_notification_handler import SendBulkNotificationHandler
from .mark_notification_read_handler import MarkNotificationReadHandler
from .mark_all_notifications_read_handler import MarkAllNotificationsReadHandler
from .delete_notification_handler import DeleteNotificationHandler
from .update_notification_preferences_handler import UpdateNotificationPreferencesHandler
from .test_email_handler import TestEmailHandler
from .test_sound_handler import TestSoundHandler

# ========== Query Handlers ==========
from .get_notifications_query_handler import GetNotificationsQueryHandler
from .get_unread_notifications_query_handler import GetUnreadNotificationsQueryHandler
from .get_notification_preferences_query_handler import GetNotificationPreferencesQueryHandler
from .get_notification_statistics_query_handler import GetNotificationStatisticsQueryHandler
from .get_email_settings_query_handler import GetEmailSettingsQueryHandler

# ========== Event Handlers ==========
from .low_stock_alert_event_handler import LowStockAlertEventHandler
from .overdue_invoice_alert_event_handler import OverdueInvoiceAlertEventHandler
from .payment_completed_notification_handler import PaymentCompletedNotificationHandler
from .approval_request_notification_handler import ApprovalRequestNotificationHandler
from .backup_completed_notification_handler import BackupCompletedNotificationHandler
from .new_user_notification_handler import NewUserNotificationHandler


__all__ = [
    # Command Handlers
    "SendNotificationHandler",
    "SendBulkNotificationHandler",
    "MarkNotificationReadHandler",
    "MarkAllNotificationsReadHandler",
    "DeleteNotificationHandler",
    "UpdateNotificationPreferencesHandler",
    "TestEmailHandler",
    "TestSoundHandler",
    
    # Query Handlers
    "GetNotificationsQueryHandler",
    "GetUnreadNotificationsQueryHandler",
    "GetNotificationPreferencesQueryHandler",
    "GetNotificationStatisticsQueryHandler",
    "GetEmailSettingsQueryHandler",
    
    # Event Handlers
    "LowStockAlertEventHandler",
    "OverdueInvoiceAlertEventHandler",
    "PaymentCompletedNotificationHandler",
    "ApprovalRequestNotificationHandler",
    "BackupCompletedNotificationHandler",
    "NewUserNotificationHandler",
]