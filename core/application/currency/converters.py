# core/application/currency/converters.py
"""
Converters for Currency - تحويل بين Domain Entities و DTOs
"""

from typing import List, Dict, Any
from uuid import UUID

from core.domain.currency.entities import Currency
from core.domain.currency.value_objects import CurrencyCode, ExchangeRate
from .dtos import CurrencyDTO, ExchangeRateDTO


def currency_to_dto(currency: Currency) -> CurrencyDTO:
    """
    تحويل كيان العملة (Domain Entity) إلى DTO
    
    Args:
        currency: كيان العملة من Domain Layer
    
    Returns:
        CurrencyDTO: كائن نقل البيانات للعملة
    """
    if not currency:
        return None
    
    # تحويل أسعار الصرف
    exchange_rates = []
    for er in currency.exchange_rates:
        exchange_rates.append(ExchangeRateDTO(
            from_currency=er.from_currency.value,
            to_currency=er.to_currency.value,
            rate=er.rate
        ))
    
    return CurrencyDTO(
        id=currency.id,
        code=currency.code.value,
        name=currency.name,
        symbol=currency.symbol,
        decimal_places=currency.decimal_places,
        is_active=currency.is_active,
        is_base=currency.is_base,
        exchange_rates=exchange_rates,
        created_at=currency.created_at,
        created_by=currency.created_by,
        updated_at=currency.updated_at,
        updated_by=currency.updated_by,
        version=currency.version
    )


def dto_to_currency(dto: CurrencyDTO) -> Currency:
    """
    تحويل DTO إلى كيان عملة
    
    Args:
        dto: كائن نقل البيانات للعملة
    
    Returns:
        Currency: كيان العملة من Domain Layer
    """
    if not dto:
        return None
    
    currency = Currency(
        id=dto.id,
        code=CurrencyCode(dto.code),
        name=dto.name,
        symbol=dto.symbol,
        decimal_places=dto.decimal_places,
        is_active=dto.is_active,
        is_base=dto.is_base,
        created_at=dto.created_at,
        created_by=dto.created_by,
        updated_at=dto.updated_at,
        updated_by=dto.updated_by,
        version=dto.version
    )
    
    # إعادة بناء أسعار الصرف
    for er_dto in dto.exchange_rates:
        currency.exchange_rates.append(ExchangeRate(
            from_currency=CurrencyCode(er_dto.from_currency),
            to_currency=CurrencyCode(er_dto.to_currency),
            rate=er_dto.rate
        ))
    
    return currency


def currency_to_dict(currency: Currency) -> Dict[str, Any]:
    """
    تحويل كيان العملة إلى قاموس للاستخدام في API أو UI
    
    Args:
        currency: كيان العملة من Domain Layer
    
    Returns:
        Dict: قاموس يحتوي على بيانات العملة
    """
    if not currency:
        return None
    
    return {
        'id': str(currency.id),
        'code': currency.code.value,
        'name': currency.name,
        'symbol': currency.symbol,
        'decimal_places': currency.decimal_places,
        'is_active': currency.is_active,
        'is_base': currency.is_base,
        'exchange_rates': [
            {
                'from_currency': er.from_currency.value,
                'to_currency': er.to_currency.value,
                'rate': er.rate
            }
            for er in currency.exchange_rates
        ],
        'created_at': currency.created_at.isoformat() if currency.created_at else None,
        'created_by': currency.created_by,
        'updated_at': currency.updated_at.isoformat() if currency.updated_at else None,
        'updated_by': currency.updated_by,
        'version': currency.version
    }


def dict_to_currency(data: Dict[str, Any]) -> Currency:
    """
    تحويل قاموس إلى كيان عملة
    
    Args:
        data: قاموس يحتوي على بيانات العملة
    
    Returns:
        Currency: كيان العملة من Domain Layer
    """
    if not data:
        return None
    
    currency = Currency(
        id=UUID(data['id']) if isinstance(data['id'], str) else data['id'],
        code=CurrencyCode(data['code']),
        name=data['name'],
        symbol=data.get('symbol', ''),
        decimal_places=data.get('decimal_places', 2),
        is_active=data.get('is_active', True),
        is_base=data.get('is_base', False),
        created_at=data.get('created_at'),
        created_by=data.get('created_by', 'system'),
        updated_at=data.get('updated_at'),
        updated_by=data.get('updated_by', 'system'),
        version=data.get('version', 1)
    )
    
    # إعادة بناء أسعار الصرف
    for er_data in data.get('exchange_rates', []):
        currency.exchange_rates.append(ExchangeRate(
            from_currency=CurrencyCode(er_data['from_currency']),
            to_currency=CurrencyCode(er_data['to_currency']),
            rate=er_data['rate']
        ))
    
    return currency


__all__ = [
    "currency_to_dto",
    "dto_to_currency",
    "currency_to_dict",
    "dict_to_currency",
]