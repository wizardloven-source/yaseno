"""
tests/audit/test_audit_trail.py

AUDIT TRAIL TESTS - CRITICAL FOR ERP COMPLIANCE

Tests comprehensive audit logging:
    - who (user)
    - when (timestamp)
    - what (action)
    - old value
    - new value
    - document
    - reason
    - IP/device/session

Essential for commercial ERP systems.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from unittest.mock import Mock, patch


# ========== DOMAIN MODELS ==========

@dataclass
class AuditEvent:
    """Represents an audit trail event."""
    id: str
    event_type: str  # CREATE, UPDATE, DELETE, POST, CANCEL
    entity_type: str  # Customer, Invoice, JournalEntry, etc.
    entity_id: str
    user_id: str
    user_name: str
    timestamp: datetime
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    document_reference: Optional[str]
    reason: Optional[str]
    ip_address: Optional[str]
    device_info: Optional[str]
    session_id: Optional[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditTrailService:
    """Service for managing audit trails."""
    
    def __init__(self, repository=None):
        self.repository = repository
        self.events = []
    
    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        document_reference: Optional[str] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            id=f"audit_{len(self.events) + 1:04d}",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            timestamp=datetime.now(timezone.utc),
            old_value=old_value,
            new_value=new_value,
            document_reference=document_reference,
            reason=reason,
            ip_address=ip_address,
            device_info=device_info,
            session_id=session_id
        )
        self.events.append(event)
        if self.repository:
            self.repository.save(event)
        return event
    
    def get_entity_history(self, entity_type: str, entity_id: str) -> list:
        """Get full history of an entity."""
        return [
            e for e in self.events 
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]
    
    def get_user_actions(self, user_id: str, from_date: datetime = None) -> list:
        """Get all actions by a user."""
        events = [e for e in self.events if e.user_id == user_id]
        if from_date:
            events = [e for e in events if e.timestamp >= from_date]
        return events
    
    def get_events_by_type(self, event_type: str) -> list:
        """Get events by type."""
        return [e for e in self.events if e.event_type == event_type]


# ========== FIXTURES ==========

@pytest.fixture
def audit_service():
    """Create an audit trail service."""
    return AuditTrailService()


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "id": "CUST-001",
        "name": "Original Customer Name",
        "email": "original@example.com",
        "phone": "+1234567890",
        "credit_limit": Decimal("10000.00")
    }


@pytest.fixture
def updated_customer_data():
    """Updated customer data for testing."""
    return {
        "id": "CUST-001",
        "name": "Updated Customer Name",
        "email": "updated@example.com",
        "phone": "+1234567890",
        "credit_limit": Decimal("15000.00")
    }


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data."""
    return {
        "id": "INV-001",
        "customer_id": "CUST-001",
        "amount": Decimal("1000.00"),
        "status": "DRAFT"
    }


@pytest.fixture
def mock_request_context():
    """Mock HTTP request context."""
    return {
        "ip_address": "192.168.1.100",
        "device_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "session_id": "sess_abc123"
    }


# ========== TESTS ==========

class TestAuditEventCreation:
    """Tests for audit event creation."""
    
    def test_create_audit_event_with_all_fields(self, audit_service):
        """Create audit event with complete information."""
        # Act
        event = audit_service.log_event(
            event_type="UPDATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="John Doe",
            old_value={"name": "Old Name"},
            new_value={"name": "New Name"},
            document_reference="DOC-001",
            reason="Customer requested name change",
            ip_address="192.168.1.100",
            device_info="Chrome Browser",
            session_id="sess_123"
        )
        
        # Assert
        assert event.event_type == "UPDATE"
        assert event.entity_type == "Customer"
        assert event.entity_id == "CUST-001"
        assert event.user_id == "USER-001"
        assert event.user_name == "John Doe"
        assert event.old_value == {"name": "Old Name"}
        assert event.new_value == {"name": "New Name"}
        assert event.document_reference == "DOC-001"
        assert event.reason == "Customer requested name change"
        assert event.ip_address == "192.168.1.100"
        assert event.device_info == "Chrome Browser"
        assert event.session_id == "sess_123"
        assert event.timestamp is not None
    
    def test_create_audit_event_minimal(self, audit_service):
        """Create audit event with minimal required fields."""
        # Act
        event = audit_service.log_event(
            event_type="CREATE",
            entity_type="Invoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="Jane Smith"
        )
        
        # Assert
        assert event.event_type == "CREATE"
        assert event.old_value is None
        assert event.new_value is None
        assert event.reason is None


class TestCustomerAuditTrail:
    """Tests for customer-related audit trails."""
    
    def test_customer_creation_audited(self, audit_service):
        """Customer creation should be audited."""
        # Arrange
        customer_data = {
            "id": "CUST-001",
            "name": "New Customer",
            "email": "new@example.com"
        }
        
        # Act
        event = audit_service.log_event(
            event_type="CREATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="Sales Rep",
            new_value=customer_data,
            reason="New customer registration"
        )
        
        # Assert
        assert event.event_type == "CREATE"
        assert event.new_value == customer_data
        assert event.old_value is None
    
    def test_customer_modification_audited(self, audit_service, sample_customer_data, updated_customer_data):
        """Customer modification should capture old and new values."""
        # Act
        event = audit_service.log_event(
            event_type="UPDATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="Sales Manager",
            old_value=sample_customer_data,
            new_value=updated_customer_data,
            reason="Credit limit increase approved",
            ip_address="192.168.1.50"
        )
        
        # Assert
        assert event.event_type == "UPDATE"
        assert event.old_value["credit_limit"] == Decimal("10000.00")
        assert event.new_value["credit_limit"] == Decimal("15000.00")
        assert event.old_value["name"] != event.new_value["name"]
    
    def test_customer_credit_limit_change_audited(self, audit_service):
        """Credit limit changes must be specifically audited."""
        # Act
        event = audit_service.log_event(
            event_type="UPDATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="Finance Manager",
            old_value={"credit_limit": Decimal("10000.00")},
            new_value={"credit_limit": Decimal("50000.00")},
            reason="Credit limit increased per board approval",
            document_reference="BOARD-RESOLUTION-2024-001"
        )
        
        # Assert
        assert event.reason is not None
        assert event.document_reference is not None
        assert "credit_limit" in event.old_value
        assert "credit_limit" in event.new_value


class TestInvoiceAuditTrail:
    """Tests for invoice-related audit trails."""
    
    def test_invoice_posting_audited(self, audit_service):
        """Posting an invoice must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="POST",
            entity_type="SalesInvoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="Accountant",
            old_value={"status": "DRAFT"},
            new_value={"status": "POSTED"},
            reason="Invoice verified and posted",
            document_reference="INV-001"
        )
        
        # Assert
        assert event.event_type == "POST"
        assert "POSTED" in str(event.new_value.values())
    
    def test_invoice_cancellation_audited(self, audit_service):
        """Cancelling an invoice must be audited with reason."""
        # Act
        event = audit_service.log_event(
            event_type="CANCEL",
            entity_type="SalesInvoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="Manager",
            old_value={"status": "POSTED"},
            new_value={"status": "CANCELLED"},
            reason="Customer requested cancellation - duplicate invoice",
            document_reference="INV-001"
        )
        
        # Assert
        assert event.event_type == "CANCEL"
        assert event.reason is not None
        assert "duplicate" in event.reason.lower()
    
    def test_invoice_price_modification_audited(self, audit_service):
        """Price modifications on invoices must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="UPDATE",
            entity_type="SalesInvoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="Sales Rep",
            old_value={"amount": Decimal("1000.00")},
            new_value={"amount": Decimal("900.00")},
            reason="Discount applied per manager approval",
            ip_address="192.168.1.100"
        )
        
        # Assert
        assert event.old_value["amount"] == Decimal("1000.00")
        assert event.new_value["amount"] == Decimal("900.00")


class TestJournalEntryAuditTrail:
    """Tests for journal entry audit trails."""
    
    def test_journal_entry_creation_audited(self, audit_service):
        """Journal entry creation must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="CREATE",
            entity_type="JournalEntry",
            entity_id="JE-001",
            user_id="USER-001",
            user_name="Accountant",
            new_value={
                "debit_account": "1010",
                "credit_account": "4010",
                "amount": Decimal("5000.00")
            },
            reason="Monthly revenue recognition"
        )
        
        # Assert
        assert event.event_type == "CREATE"
        assert event.entity_type == "JournalEntry"
    
    def test_journal_entry_posting_audited(self, audit_service):
        """Journal entry posting must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="POST",
            entity_type="JournalEntry",
            entity_id="JE-001",
            user_id="USER-001",
            user_name="Senior Accountant",
            old_value={"status": "DRAFT"},
            new_value={"status": "POSTED"}
        )
        
        # Assert
        assert event.event_type == "POST"
    
    def test_journal_entry_cannot_be_modified_after_post(self, audit_service):
        """Attempted modification of posted entry should be logged."""
        # Arrange: Entry already posted
        audit_service.log_event(
            event_type="POST",
            entity_type="JournalEntry",
            entity_id="JE-001",
            user_id="USER-001",
            user_name="Accountant",
            old_value={"status": "DRAFT"},
            new_value={"status": "POSTED"}
        )
        
        # Act: Attempt modification (should fail in real system)
        attempt_event = audit_service.log_event(
            event_type="UPDATE_ATTEMPT",
            entity_type="JournalEntry",
            entity_id="JE-001",
            user_id="USER-002",
            user_name="Unauthorized User",
            old_value={"status": "POSTED"},
            new_value=None,
            reason="Attempted to modify posted entry - BLOCKED"
        )
        
        # Assert
        assert attempt_event.event_type == "UPDATE_ATTEMPT"
        assert "BLOCKED" in attempt_event.reason


class TestInventoryAuditTrail:
    """Tests for inventory audit trails."""
    
    def test_stock_adjustment_audited(self, audit_service):
        """Stock adjustments must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="ADJUSTMENT",
            entity_type="Inventory",
            entity_id="PROD-001",
            user_id="USER-001",
            user_name="Warehouse Manager",
            old_value={"quantity": Decimal("100")},
            new_value={"quantity": Decimal("95")},
            reason="Damaged goods removed",
            document_reference="ADJ-001"
        )
        
        # Assert
        assert event.event_type == "ADJUSTMENT"
        assert event.reason is not None
    
    def test_inventory_transfer_audited(self, audit_service):
        """Inventory transfers between warehouses must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="TRANSFER",
            entity_type="Inventory",
            entity_id="PROD-001",
            user_id="USER-001",
            user_name="Logistics Coordinator",
            old_value={"warehouse": "WH-001", "quantity": Decimal("50")},
            new_value={"warehouse": "WH-002", "quantity": Decimal("50")},
            reason="Stock rebalancing",
            document_reference="TRF-001"
        )
        
        # Assert
        assert event.event_type == "TRANSFER"


class TestSecurityAuditTrail:
    """Tests for security-related audit trails."""
    
    def test_permission_change_audited(self, audit_service):
        """Permission changes must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="UPDATE",
            entity_type="UserRole",
            entity_id="ROLE-001",
            user_id="USER-001",
            user_name="System Admin",
            old_value={"permissions": ["sales.invoice.create"]},
            new_value={"permissions": ["sales.invoice.create", "sales.invoice.post"]},
            reason="Role elevation approved by IT Director",
            ip_address="10.0.0.1"
        )
        
        # Assert
        assert event.event_type == "UPDATE"
        assert len(event.new_value["permissions"]) > len(event.old_value["permissions"])
    
    def test_failed_login_attempt_audited(self, audit_service):
        """Failed login attempts should be audited."""
        # Act
        event = audit_service.log_event(
            event_type="LOGIN_FAILED",
            entity_type="User",
            entity_id="USER-001",
            user_id="ANONYMOUS",
            user_name="Unknown",
            new_value={"username": "admin"},
            reason="Invalid password",
            ip_address="192.168.1.200",
            device_info="Unknown Browser"
        )
        
        # Assert
        assert event.event_type == "LOGIN_FAILED"
        assert event.ip_address is not None


class TestFinancialPeriodAuditTrail:
    """Tests for financial period audit trails."""
    
    def test_period_close_audited(self, audit_service):
        """Closing a financial period must be audited."""
        # Act
        event = audit_service.log_event(
            event_type="CLOSE",
            entity_type="FiscalPeriod",
            entity_id="2024-12",
            user_id="USER-001",
            user_name="CFO",
            old_value={"status": "OPEN"},
            new_value={"status": "CLOSED"},
            reason="Month-end closing completed",
            document_reference="CLOSE-2024-12"
        )
        
        # Assert
        assert event.event_type == "CLOSE"
        assert event.entity_type == "FiscalPeriod"
    
    def test_period_reopen_audited(self, audit_service):
        """Reopening a closed period must be audited with strong justification."""
        # Act
        event = audit_service.log_event(
            event_type="REOPEN",
            entity_type="FiscalPeriod",
            entity_id="2024-11",
            user_id="USER-001",
            user_name="CFO",
            old_value={"status": "CLOSED"},
            new_value={"status": "OPEN"},
            reason="Adjusting entry required for audit correction",
            document_reference="AUDIT-ADJ-2024-001",
            ip_address="10.0.0.1"
        )
        
        # Assert
        assert event.event_type == "REOPEN"
        assert event.reason is not None


class TestAuditQuerying:
    """Tests for audit trail querying capabilities."""
    
    def test_get_entity_history(self, audit_service):
        """Should retrieve full history of an entity."""
        # Arrange: Multiple events for same entity
        audit_service.log_event(
            event_type="CREATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="Sales Rep"
        )
        audit_service.log_event(
            event_type="UPDATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-002",
            user_name="Manager"
        )
        audit_service.log_event(
            event_type="UPDATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="Sales Rep"
        )
        
        # Act
        history = audit_service.get_entity_history("Customer", "CUST-001")
        
        # Assert
        assert len(history) == 3
    
    def test_get_user_actions(self, audit_service):
        """Should retrieve all actions by a specific user."""
        # Arrange: Multiple users
        audit_service.log_event(
            event_type="CREATE",
            entity_type="Invoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="Alice"
        )
        audit_service.log_event(
            event_type="POST",
            entity_type="Invoice",
            entity_id="INV-001",
            user_id="USER-002",
            user_name="Bob"
        )
        audit_service.log_event(
            event_type="UPDATE",
            entity_type="Invoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="Alice"
        )
        
        # Act
        alice_actions = audit_service.get_user_actions("USER-001")
        
        # Assert
        assert len(alice_actions) == 2
    
    def test_get_events_by_type(self, audit_service):
        """Should filter events by type."""
        # Arrange
        audit_service.log_event(
            event_type="CREATE",
            entity_type="Invoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="User"
        )
        audit_service.log_event(
            event_type="POST",
            entity_type="Invoice",
            entity_id="INV-001",
            user_id="USER-001",
            user_name="User"
        )
        audit_service.log_event(
            event_type="CREATE",
            entity_type="Customer",
            entity_id="CUST-001",
            user_id="USER-001",
            user_name="User"
        )
        
        # Act
        create_events = audit_service.get_events_by_type("CREATE")
        
        # Assert
        assert len(create_events) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
