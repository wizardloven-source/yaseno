# core/application/handlers/payments/payment_completed_event_handler.py
"""Payment Completed Event Handler - معالج حدث إكمال الدفعة"""

import logging

from core.domain.payments.events import PaymentCompletedEvent
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.accounting.interfaces import IUnitOfWork

logger = logging.getLogger(__name__)


class PaymentCompletedEventHandler:
    """
    معالج حدث إكمال الدفعة
    
    مسؤولياته:
        1. الاستماع لحدث PaymentCompletedEvent
        2. إنشاء قيد محاسبي تلقائياً
        3. تحديث رصيد الصندوق
    """
    
    def __init__(self, uow: IUnitOfWork, posting_engine: PostingEngine):
        self._uow = uow
        self._posting_engine = posting_engine
    
    def __call__(self, event: PaymentCompletedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث إكمال الدفعة
        """
        try:
            logger.info(f"Processing PaymentCompletedEvent for payment {event.payment_code}")
            
            # هنا يمكن إضافة منطق إضافي مثل:
            # - تحديث رصيد العميل/المورد
            # - إرسال إشعار
            # - تحديث التقارير
            
            # يتم إنشاء القيد المحاسبي بالفعل في CompletePaymentHandler
            # هذا المعالج يمكن استخدامه لإجراءات إضافية بعد الإكمال
            
        except Exception as e:
            logger.error(f"Error processing PaymentCompletedEvent: {e}", exc_info=True)