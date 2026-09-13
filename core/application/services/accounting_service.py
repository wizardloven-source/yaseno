"""
YASeen ERP - Application Services
Implements: Accounting Service, Audit Service, Permission Service
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from core.domain.models import (
    JournalEntry, JournalEntryLine, FinancialPeriod, 
    PeriodStatus, EntryStatus, AuditEvent, User, Permission
)


class AccountingService:
    """Core Accounting Operations with Invariant Enforcement"""
    
    def __init__(self, period_repo, entry_repo, audit_service):
        self.period_repo = period_repo
        self.entry_repo = entry_repo
        self.audit_service = audit_service

    def create_entry(
        self,
        date: datetime.date,
        lines: List[Dict[str, Any]],
        reference: str = "",
        description: str = "",
        user: User = None,
        base_currency: str = "USD"
    ) -> JournalEntry:
        """Create a new journal entry (Draft status)"""
        
        # Find financial period
        period = self._find_period(date)
        
        # Convert line dicts to JournalEntryLine objects
        entry_lines = []
        for line in lines:
            amount_currency = Decimal(str(line.get('amount_currency', 0)))
            exchange_rate = Decimal(str(line.get('exchange_rate', 1)))
            
            # Calculate base currency amounts
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            
            if amount_currency > 0 and (debit == 0 and credit == 0):
                # Convert from foreign currency to base
                debit = amount_currency * exchange_rate if line.get('is_debit', False) else Decimal(0)
                credit = amount_currency * exchange_rate if not line.get('is_debit', False) else Decimal(0)
            
            entry_lines.append(JournalEntryLine(
                account_id=line['account_id'],
                debit=debit,
                credit=credit,
                currency_code=line.get('currency_code', base_currency),
                amount_currency=amount_currency,
                exchange_rate=exchange_rate,
                description=line.get('description', '')
            ))
        
        entry = JournalEntry(
            date=date,
            period_id=period.name,
            lines=entry_lines,
            reference=reference,
            description=description,
            base_currency=base_currency,
            exchange_rate_date=date
        )
        
        # Validate balance before saving
        entry.validate_balance()
        
        # Save as draft
        self.entry_repo.save(entry)
        
        # Audit trail
        if user:
            self.audit_service.log(
                user=user,
                action="CREATE",
                entity_type="JournalEntry",
                entity_id=entry.id,
                new_values={"reference": reference, "lines_count": len(lines)},
                reason="Created new journal entry"
            )
        
        return entry

    def post_entry(self, entry_id: str, user: User) -> JournalEntry:
        """Post a journal entry (enforces period check and balance)"""
        
        entry = self.entry_repo.get(entry_id)
        if not entry:
            raise ValueError(f"Journal Entry {entry_id} not found")
        
        period = self.period_repo.get_by_name(entry.period_id)
        if not period:
            raise ValueError(f"Financial Period {entry.period_id} not found")
        
        old_status = entry.status.value
        
        # This enforces the Financial Period constraint in CORE
        entry.post(user.id, period)
        
        # Audit trail
        self.audit_service.log(
            user=user,
            action="POST",
            entity_type="JournalEntry",
            entity_id=entry.id,
            old_values={"status": old_status},
            new_values={"status": entry.status.value, "posted_by": user.id},
            reason="Posted journal entry"
        )
        
        self.entry_repo.save(entry)
        return entry

    def cancel_entry(self, entry_id: str, user: User, reason: str = "") -> JournalEntry:
        """Cancel a posted entry"""
        
        entry = self.entry_repo.get(entry_id)
        if not entry:
            raise ValueError(f"Journal Entry {entry_id} not found")
        
        old_status = entry.status.value
        entry.cancel(user.id)
        
        self.audit_service.log(
            user=user,
            action="CANCEL",
            entity_type="JournalEntry",
            entity_id=entry.id,
            old_values={"status": old_status},
            new_values={"status": entry.status.value},
            reason=reason or "Cancelled by user"
        )
        
        self.entry_repo.save(entry)
        return entry

    def reverse_entry(self, original_entry_id: str, user: User, reason: str = "") -> JournalEntry:
        """Create a reversing entry for a posted entry"""
        
        original = self.entry_repo.get(original_entry_id)
        if not original:
            raise ValueError(f"Journal Entry {original_entry_id} not found")
        
        if original.status != EntryStatus.POSTED:
            raise ValueError("Only posted entries can be reversed")
        
        # Create reversed lines
        reversed_lines = []
        for line in original.lines:
            reversed_lines.append(JournalEntryLine(
                account_id=line.account_id,
                debit=line.credit,  # Swap debit/credit
                credit=line.debit,
                currency_code=line.currency_code,
                amount_currency=line.amount_currency,
                exchange_rate=line.exchange_rate,
                description=f"Reversal of {original.reference}"
            ))
        
        reversal = self.create_entry(
            date=datetime.now().date(),
            lines=[{
                'account_id': l.account_id,
                'debit': float(l.debit),
                'credit': float(l.credit),
                'currency_code': l.currency_code,
                'amount_currency': float(l.amount_currency),
                'exchange_rate': float(l.exchange_rate),
                'description': l.description
            } for l in reversed_lines],
            reference=f"REV-{original.reference}",
            description=f"Reversal of {original.id}: {reason}",
            user=user,
            base_currency=original.base_currency
        )
        
        # Auto-post the reversal
        period = self.period_repo.get_by_name(reversal.period_id)
        reversal.post(user.id, period)
        self.entry_repo.save(reversal)
        
        self.audit_service.log(
            user=user,
            action="REVERSE",
            entity_type="JournalEntry",
            entity_id=reversal.id,
            new_values={"reverses": original.id, "reason": reason},
            reason=f"Created reversal for {original.id}"
        )
        
        return reversal

    def _find_period(self, target_date: datetime.date) -> FinancialPeriod:
        """Find the financial period for a given date"""
        periods = self.period_repo.get_all()
        for period in periods:
            if period.is_date_within(target_date):
                return period
        raise ValueError(f"No financial period found for date {target_date}")


class AuditService:
    """Centralized Audit Trail Management"""
    
    def __init__(self, audit_repo):
        self.audit_repo = audit_repo

    def log(
        self,
        user: User,
        action: str,
        entity_type: str,
        entity_id: str,
        old_values: Dict[str, Any] = None,
        new_values: Dict[str, Any] = None,
        reason: str = "",
        ip_address: str = "",
        device_info: str = "",
        session_id: str = ""
    ) -> AuditEvent:
        event = AuditEvent(
            user_id=user.id,
            user_name=user.username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values or {},
            new_values=new_values or {},
            reason=reason,
            ip_address=ip_address,
            device_info=device_info,
            session_id=session_id
        )
        
        self.audit_repo.save(event)
        return event

    def get_history(self, entity_type: str, entity_id: str) -> List[AuditEvent]:
        return self.audit_repo.get_by_entity(entity_type, entity_id)


class PermissionService:
    """Hierarchical Permission Management"""
    
    def __init__(self, role_repo, permission_repo):
        self.role_repo = role_repo
        self.permission_repo = permission_repo

    def check_permission(self, user: User, permission_code: str) -> bool:
        """Check if user has specific permission (e.g., sales.invoice.post)"""
        return user.can(permission_code)

    def require_permission(self, user: User, permission_code: str):
        """Raise error if user lacks permission"""
        if not self.check_permission(user, permission_code):
            raise PermissionError(
                f"User {user.username} lacks permission: {permission_code}"
            )

    def create_permission(self, module: str, screen: str, action: str) -> Permission:
        code = f"{module}.{screen}.{action}"
        return Permission.parse(code)

    def grant_permission(self, role_id: str, permission_code: str):
        role = self.role_repo.get(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if permission_code not in role.permissions:
            old_perms = role.permissions.copy()
            role.permissions.append(permission_code)
            self.role_repo.save(role)
            
            # Audit this change
            # (Would need audit_service injected or called separately)

    def revoke_permission(self, role_id: str, permission_code: str):
        role = self.role_repo.get(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if permission_code in role.permissions:
            role.permissions.remove(permission_code)
            self.role_repo.save(role)
