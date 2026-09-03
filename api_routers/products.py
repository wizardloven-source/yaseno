# api_routers/products.py
"""
YAseen ERP - Products Router
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query, Depends, status, HTTPException
from starlette.status import HTTP_201_CREATED

from api_routers.shared import (
    bootstrap, logger, ApiResponse, CreateProductRequest, get_current_user,
    filter_fields,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["products"])


@router.get("/api/products", response_model=ApiResponse)
async def list_products(
    include_inactive: bool = Query(False),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            products = uow.products.list_all(
                include_inactive=include_inactive,
                category=category,
                limit=limit,
                offset=offset,
            )
            if q:
                ql = q.lower()
                products = [p for p in products if ql in str(p.code).lower() or ql in (p.name or '').lower()]
            result = []
            for p in products:
                result.append({
                    'id': str(p.id.value),
                    'code': str(p.code),
                    'name': p.name,
                    'unit_price': float(p.unit_price.amount),
                    'currency': p.unit_price.currency,
                    'tax_rate': float(p.tax_rate),
                    'category': p.category,
                    'stock_quantity': p.stock_quantity,
                    'low_stock_threshold': p.low_stock_threshold,
                    'status': p.status.value if hasattr(p.status, 'value') else str(p.status),
                })
            return ApiResponse(success=True, message="تم جلب المنتجات بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing products: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/products", response_model=ApiResponse, status_code=HTTP_201_CREATED)
async def create_product(request: CreateProductRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("products.create_product"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.domain.products.entities import Product
        from core.domain.products.value_objects import ProductCode
        from core.domain.shared.value_objects import Money

        with bootstrap.uow() as uow:
            existing = uow.products.get_by_code(ProductCode(request.code))
            if existing:
                return ApiResponse(success=False, message=f"كود المنتج '{request.code}' مستخدم مسبقاً", errors=[f"كود المنتج '{request.code}' مستخدم مسبقاً"])

        product = Product.create(
            code=ProductCode(request.code),
            name=request.name,
            unit_price=Money(request.unit_price, request.currency),
            tax_rate=request.tax_rate,
            description=request.description,
            category=request.category,
            stock_quantity=request.stock_quantity,
            low_stock_threshold=request.low_stock_threshold,
            created_by=current_user["username"],
        )
        with bootstrap.uow() as uow:
            uow.products.save(product)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء المنتج بنجاح",
                           data={'id': str(product.id.value), 'code': str(product.code), 'name': product.name})
    except Exception as e:
        logger.error(f"Error creating product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/products/low-stock", response_model=ApiResponse)
async def get_low_stock_products(
    threshold: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.products
            all_products = repo.get_all() if hasattr(repo, 'get_all') else []
            result = []
            for p in all_products:
                if getattr(p, 'stock_quantity', 0) <= threshold:
                    result.append({
                        'id': str(getattr(p, 'id', '')),
                        'code': str(getattr(p, 'code', '')),
                        'name': getattr(p, 'name', ''),
                        'stock_quantity': getattr(p, 'stock_quantity', 0),
                    })
            return ApiResponse(success=True, message="تم جلب المنتجات منخفضة المخزون بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting low stock products: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/products/{product_id}", response_model=ApiResponse)
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.products.value_objects import ProductId
        with bootstrap.uow() as uow:
            product = uow.products.get_by_id(ProductId.from_string(product_id))
            if not product:
                return ApiResponse(success=False, message="المنتج غير موجود")
            data = {
                'id': str(product.id.value),
                'code': str(product.code),
                'name': product.name,
                'unit_price': float(product.unit_price.amount),
                'currency': product.unit_price.currency,
                'tax_rate': float(product.tax_rate),
                'description': product.description,
                'category': product.category,
                'stock_quantity': product.stock_quantity,
                'low_stock_threshold': product.low_stock_threshold,
                'status': product.status.value if hasattr(product.status, 'value') else str(product.status),
                'version': product.version,
            }
            return ApiResponse(success=True, message="تم جلب المنتج بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/products/{product_id}", response_model=ApiResponse)
async def update_product(product_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("products.update_product"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        data = filter_fields(request, [
            "name", "unit_price", "is_active", "stock_quantity", "status",
            "currency", "tax_rate", "description", "category",
        ])
        with bootstrap.uow() as uow:
            repo = uow.products
            product = repo.get_by_id(product_id) if hasattr(repo, 'get_by_id') else None
            if not product:
                return ApiResponse(success=False, message="المنتج غير موجود")
            if 'name' in data:
                product.name = data['name']
            if 'unit_price' in data:
                val = data['unit_price']
                if isinstance(val, str):
                    val = Decimal(val)
                elif isinstance(val, (int, float)):
                    val = Decimal(str(val))
                product.unit_price = val
            if 'is_active' in data:
                product.is_active = bool(data['is_active'])
            if 'status' in data:
                from core.domain.products.value_objects import ProductStatus
                status_map = {s.value: s for s in ProductStatus}
                new_status = data['status']
                if new_status in status_map:
                    product.status = status_map[new_status]
                    product.is_active = (new_status == 'active')
            if 'stock_quantity' in data:
                product.stock_quantity = int(data['stock_quantity'])
            if 'tax_rate' in data:
                product.tax_rate = Decimal(str(data['tax_rate']))
            if 'description' in data:
                product.description = data['description']
            if 'category' in data:
                product.category = data['category']
            product.updated_by = current_user["username"]
            repo.save(product)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المنتج بنجاح")
    except Exception as e:
        logger.error(f"Error updating product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/products/{product_id}/stock", response_model=ApiResponse)
async def update_product_stock(product_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, ["quantityChange"])
        with bootstrap.uow() as uow:
            repo = uow.products
            product = repo.get_by_id(product_id) if hasattr(repo, 'get_by_id') else None
            if not product:
                return ApiResponse(success=False, message="المنتج غير موجود")
            quantity_change = data.get('quantityChange', 0)
            product.stock_quantity = getattr(product, 'stock_quantity', 0) + quantity_change
            product.updated_by = current_user["username"]
            repo.save(product)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المخزون بنجاح")
    except Exception as e:
        logger.error(f"Error updating product stock: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/products/{product_id}", response_model=ApiResponse)
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("products.delete_product"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        with bootstrap.uow() as uow:
            repo = uow.products
            repo.delete(product_id)
            uow.commit()
            return ApiResponse(success=True, message="تم حذف المنتج بنجاح")
    except Exception as e:
        logger.error(f"Error deleting product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
