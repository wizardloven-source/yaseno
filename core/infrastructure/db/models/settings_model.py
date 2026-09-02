# core/infrastructure/db/models/settings_model.py
"""Settings ORM Model - تخزين الإعدادات في JSONB"""

from sqlalchemy import String, Integer, DateTime, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

from .account_model import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class SettingsModel(Base):
    """نموذج تخزين الإعدادات - يستخدم JSONB للتخزين المرن"""
    __tablename__ = "system_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    
    # البيانات الرئيسية مخزنة كـ JSONB
    settings_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # بيانات التدقيق
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    
    __table_args__ = (
        Index("idx_settings_version", "version"),
    )
    
    def __repr__(self) -> str:
        return f"SettingsModel(version={self.version}, updated_at={self.updated_at})"


# ✅ إضافة نموذج إعدادات الحسابات المحاسبية
class AccountingSettingsModel(Base):
    """نموذج إعدادات الحسابات المحاسبية"""
    __tablename__ = "accounting_settings"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="default")
    
    # حسابات الفواتير
    sales_revenue_account: Mapped[str] = mapped_column(String(20), default="4010")
    cash_account: Mapped[str] = mapped_column(String(20), default="1010")
    receivables_account: Mapped[str] = mapped_column(String(20), default="1020")
    
    # حسابات المشتريات
    inventory_account: Mapped[str] = mapped_column(String(20), default="1030")
    payables_account: Mapped[str] = mapped_column(String(20), default="2010")
    
    # حسابات الإقفال
    income_summary_account: Mapped[str] = mapped_column(String(20), default="3990")
    retained_earnings_account: Mapped[str] = mapped_column(String(20), default="3010")
    
    # حسابات أخرى
    cogs_account: Mapped[str] = mapped_column(String(20), default="5010")
    tax_account: Mapped[str] = mapped_column(String(20), default="2100")
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    
    def __repr__(self) -> str:
        return f"AccountingSettingsModel(id={self.id})"