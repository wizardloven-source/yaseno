from fastapi import APIRouter
from api_routers.shared import ApiResponse, bootstrap, logger

router = APIRouter(prefix="", tags=["health"])


@router.get("/api/health", response_model=ApiResponse)
async def health_check():
    return ApiResponse(
        success=True,
        message="الخادم يعمل بشكل صحيح",
        data={"status": "healthy", "version": "3.0.0"}
    )


@router.get("/api/health/db", response_model=ApiResponse)
async def health_check_db():
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            result = uow.session.execute(text("SELECT 1"))
            return ApiResponse(
                success=True,
                message="قاعدة البيانات متصلة بشكل صحيح",
                data={"status": "connected"}
            )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ApiResponse(
            success=False,
            message=f"فشل الاتصال بقاعدة البيانات: {str(e)}",
            errors=[str(e)]
        )
