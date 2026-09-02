# core/application/products/converters.py

"""
Converters for Products - تحويل بين Domain Entities و DTOs
"""

from core.domain.products.entities import Product
from .dtos import ProductDTO, ProductSummaryDTO


def product_to_dto(product: Product) -> ProductDTO:
    """تحويل كيان المنتج إلى DTO"""
    if not product:
        return None
    
    return ProductDTO(
        id=str(product.id.value),
        code=product.code.value,
        name=product.name,
        description=product.description,
        category=product.category,
        unit_price=product.unit_price.amount,
        currency=product.unit_price.currency,
        tax_rate=product.tax_rate,
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        version=product.version,
    )


def product_to_summary_dto(product: Product) -> ProductSummaryDTO:
    """تحويل كيان المنتج إلى Summary DTO"""
    if not product:
        return None
    
    return ProductSummaryDTO(
        id=str(product.id.value),
        code=product.code.value,
        name=product.name,
        unit_price=product.unit_price.amount,
        currency=product.unit_price.currency,
        stock_quantity=product.stock_quantity,
    )


__all__ = [
    "product_to_dto",
    "product_to_summary_dto",
]