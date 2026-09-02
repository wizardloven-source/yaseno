# tests/unit/handlers/test_payment_handlers.py
"""اختبارات معالجات الدفعات"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from core.domain.payments.entities import Payment
from core.domain.payments.value_objects import PaymentType, PaymentMethod, Money
from core.application.payments.commands import CreatePaymentCommand, CompletePaymentCommand
from core.application.handlers.payments import CreatePaymentHandler, CompletePaymentHandler
from core.application.security.authorization import UserContext


class TestCreatePaymentHandler:
    """اختبارات معالج إنشاء دفعة"""
    
    def test_create_payment_success(self):
        """اختبار إنشاء دفعة بنجاح"""
        # Arrange
        mock_uow = Mock()
        mock_repo = Mock()
        mock_uow.payments = mock_repo
        
        handler = CreatePaymentHandler(mock_uow)
        
        command = CreatePaymentCommand(
            payment_type="receive",
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method="cash",
            customer_name="عميل تجريبي",
            created_by="test_user"
        )
        
        user_context = UserContext(
            user_id="test_user",
            username="Test User",
            roles=["admin"]
        )
        
        # Act
        result = handler.handle(command, user_context)
        
        # Assert
        assert result is not None
        assert result.code is not None
        assert result.amount == Decimal("1000.00")
        assert result.payment_type == PaymentType.RECEIVE
        assert result.customer_name == "عميل تجريبي"
        
        mock_repo.save.assert_called_once()


class TestCompletePaymentHandler:
    """اختبارات معالج إكمال دفعة"""
    
    def test_complete_payment_success(self):
        """اختبار إكمال دفعة بنجاح"""
        # Arrange
        mock_uow = Mock()
        mock_repo = Mock()
        mock_uow.payments = mock_repo
        
        # إنشاء دفعة وهمية
        payment = Payment.create(
            payment_type=PaymentType.RECEIVE,
            amount=Money(Decimal("1000.00"), "USD"),
            payment_method=PaymentMethod.CASH,
            customer_name="عميل تجريبي"
        )
        
        mock_repo.get_by_id.return_value = payment
        
        handler = CompletePaymentHandler(mock_uow, Mock())
        
        command = CompletePaymentCommand(
            payment_id=str(payment.id),
            completed_by="test_user"
        )
        
        user_context = UserContext(
            user_id="test_user",
            username="Test User",
            roles=["admin"]
        )
        
        # Act
        result = handler.handle(command, user_context)
        
        # Assert
        assert result is not None
        assert result.status == PaymentStatus.COMPLETED
        
        mock_repo.save.assert_called_once()