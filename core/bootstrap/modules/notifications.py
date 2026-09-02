# core/bootstrap/modules/notifications.py
"""
وحدة الإشعارات - تسجيل جميع خدمات الإشعارات
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module, lazy_event_handler

logger = logging.getLogger(__name__)


class NotificationsModule(Module):
    """
    وحدة الإشعارات - نظام الإشعارات المتقدم
    
    تشمل:
        1. إشعارات النظام (System Notifications)
        2. إشعارات البريد الإلكتروني (Email Notifications)
        3. إشعارات صوتية (Sound Notifications)
        4. إشعارات تنبيه المخزون المنخفض
        5. إشعارات الفواتير المتأخرة
        6. إشعارات المستخدمين الجدد
        7. إشعارات تحديثات النظام
        8. إشعارات النسخ الاحتياطي
        9. إشعارات الموافقات (Approval Notifications)
        10. إشعارات الدفعات (Payment Notifications)
    """
    
    name = "notifications"
    description = "نظام الإشعارات - تنبيهات النظام، البريد الإلكتروني، والإشعارات الصوتية"
    dependencies = ["database", "settings", "security"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الإشعارات"""
        
        # ========== Repositories ==========
        container.register(
            "notification_repo",
            "core.infrastructure.db.postgres.notification_repository.PostgresNotificationRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "notification_template_repo",
            "core.infrastructure.db.postgres.notification_repository.PostgresNotificationTemplateRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "notification_preference_repo",
            "core.infrastructure.db.postgres.notification_repository.PostgresNotificationPreferenceRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "notification_service",
            "core.application.notifications.services.NotificationService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["notification_repo", "uow"]
        )
        container.register(
            "email_service",
            "core.application.notifications.services.EmailService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["settings_repo"]
        )
        container.register(
            "sound_service",
            "core.application.notifications.services.SoundService",
            lifetime=ServiceLifetime.SINGLETON
        )
        container.register(
            "notification_preference_service",
            "core.application.notifications.services.NotificationPreferenceService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["notification_preference_repo", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "send_notification_handler",
            "core.application.handlers.notifications.SendNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "send_bulk_notification_handler",
            "core.application.handlers.notifications.SendBulkNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "mark_notification_read_handler",
            "core.application.handlers.notifications.MarkNotificationReadHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "mark_all_notifications_read_handler",
            "core.application.handlers.notifications.MarkAllNotificationsReadHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_notification_handler",
            "core.application.handlers.notifications.DeleteNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_notification_preferences_handler",
            "core.application.handlers.notifications.UpdateNotificationPreferencesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_preference_service"]
        )
        container.register(
            "test_email_handler",
            "core.application.handlers.notifications.TestEmailHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "email_service"]
        )
        container.register(
            "test_sound_handler",
            "core.application.handlers.notifications.TestSoundHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["sound_service"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_notifications_handler",
            "core.application.handlers.notifications.GetNotificationsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["notification_repo"]
        )
        container.register(
            "get_unread_notifications_handler",
            "core.application.handlers.notifications.GetUnreadNotificationsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["notification_repo"]
        )
        container.register(
            "get_notification_preferences_handler",
            "core.application.handlers.notifications.GetNotificationPreferencesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["notification_preference_repo"]
        )
        container.register(
            "get_notification_statistics_handler",
            "core.application.handlers.notifications.GetNotificationStatisticsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["notification_repo"]
        )
        container.register(
            "get_email_settings_handler",
            "core.application.handlers.notifications.GetEmailSettingsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["settings_repo"]
        )
        
        # ========== Event Handlers ==========
        container.register(
            "low_stock_alert_handler",
            "core.application.handlers.notifications.LowStockAlertEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "overdue_invoice_alert_handler",
            "core.application.handlers.notifications.OverdueInvoiceAlertEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "payment_completed_notification_handler",
            "core.application.handlers.notifications.PaymentCompletedNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "approval_request_notification_handler",
            "core.application.handlers.notifications.ApprovalRequestNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "backup_completed_notification_handler",
            "core.application.handlers.notifications.BackupCompletedNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "new_user_notification_handler",
            "core.application.handlers.notifications.NewUserNotificationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus و Event Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        event_bus = container.resolve("event_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("SendNotificationCommand", "send_notification_handler")
                logger.info("✅ Registered SendNotificationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register SendNotificationCommand: {e}")
            
            try:
                command_bus.register("SendBulkNotificationCommand", "send_bulk_notification_handler")
                logger.info("✅ Registered SendBulkNotificationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register SendBulkNotificationCommand: {e}")
            
            try:
                command_bus.register("MarkNotificationReadCommand", "mark_notification_read_handler")
                logger.info("✅ Registered MarkNotificationReadCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register MarkNotificationReadCommand: {e}")
            
            try:
                command_bus.register("MarkAllNotificationsReadCommand", "mark_all_notifications_read_handler")
                logger.info("✅ Registered MarkAllNotificationsReadCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register MarkAllNotificationsReadCommand: {e}")
            
            try:
                command_bus.register("DeleteNotificationCommand", "delete_notification_handler")
                logger.info("✅ Registered DeleteNotificationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteNotificationCommand: {e}")
            
            try:
                command_bus.register("UpdateNotificationPreferencesCommand", "update_notification_preferences_handler")
                logger.info("✅ Registered UpdateNotificationPreferencesCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateNotificationPreferencesCommand: {e}")
            
            try:
                command_bus.register("TestEmailCommand", "test_email_handler")
                logger.info("✅ Registered TestEmailCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register TestEmailCommand: {e}")
            
            try:
                command_bus.register("TestSoundCommand", "test_sound_handler")
                logger.info("✅ Registered TestSoundCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register TestSoundCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetNotificationsQuery", "get_notifications_handler")
                logger.info("✅ Registered GetNotificationsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetNotificationsQuery: {e}")
            
            try:
                query_bus.register("GetUnreadNotificationsQuery", "get_unread_notifications_handler")
                logger.info("✅ Registered GetUnreadNotificationsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetUnreadNotificationsQuery: {e}")
            
            try:
                query_bus.register("GetNotificationPreferencesQuery", "get_notification_preferences_handler")
                logger.info("✅ Registered GetNotificationPreferencesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetNotificationPreferencesQuery: {e}")
            
            try:
                query_bus.register("GetNotificationStatisticsQuery", "get_notification_statistics_handler")
                logger.info("✅ Registered GetNotificationStatisticsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetNotificationStatisticsQuery: {e}")
            
            try:
                query_bus.register("GetEmailSettingsQuery", "get_email_settings_handler")
                logger.info("✅ Registered GetEmailSettingsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetEmailSettingsQuery: {e}")
            
            # ========== Event Handlers ==========
            # ✅ جميعها تُحل في نطاق جديد (جلسة جديدة) لكل حدث
            try:
                event_bus.add_handler("LowStockAlertEvent", lazy_event_handler(scoped_container, "low_stock_alert_handler"))
                logger.info("✅ Registered LowStockAlertEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register LowStockAlertEventHandler: {e}")
            
            try:
                event_bus.add_handler("InvoiceOverdueEvent", lazy_event_handler(scoped_container, "overdue_invoice_alert_handler"))
                logger.info("✅ Registered OverdueInvoiceAlertEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register OverdueInvoiceAlertEventHandler: {e}")
            
            try:
                event_bus.add_handler("PaymentCompletedEvent", lazy_event_handler(scoped_container, "payment_completed_notification_handler"))
                logger.info("✅ Registered PaymentCompletedNotificationHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register PaymentCompletedNotificationHandler: {e}")
            
            try:
                event_bus.add_handler("ApprovalRequestSubmittedEvent", lazy_event_handler(scoped_container, "approval_request_notification_handler"))
                logger.info("✅ Registered ApprovalRequestNotificationHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register ApprovalRequestNotificationHandler: {e}")
            
            try:
                event_bus.add_handler("BackupCompletedEvent", lazy_event_handler(scoped_container, "backup_completed_notification_handler"))
                logger.info("✅ Registered BackupCompletedNotificationHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register BackupCompletedNotificationHandler: {e}")
            
            try:
                event_bus.add_handler("UserCreatedEvent", lazy_event_handler(scoped_container, "new_user_notification_handler"))
                logger.info("✅ Registered NewUserNotificationHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register NewUserNotificationHandler: {e}")