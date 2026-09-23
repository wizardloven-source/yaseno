"""
Projects Router - إدارة المشاريع والميزانيات والمصروفات
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ConfigDict

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user

router = APIRouter(prefix="", tags=["projects"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ProjectBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def _clean(self, exclude_none=True) -> Dict[str, Any]:
        """إرجاع القيم المحددة فقط (تجاهل None للتمييز بين غير المحدد والمحدد صراحة)"""
        data = self.model_dump(exclude_none=exclude_none)
        return data


class CreateProjectRequest(ProjectBaseModel):
    name: str = Field(..., min_length=2, max_length=200, description="اسم المشروع")
    code: Optional[str] = Field(None, max_length=50, description="كود المشروع (يُولّد تلقائياً إذا فُوّض)")
    description: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    budget_amount: Optional[Decimal] = Field(None, ge=0, description="الميزانية")
    budget_currency: Optional[str] = Field("USD", max_length=3)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = "planning"
    tags: Optional[List[str]] = None


class UpdateProjectRequest(ProjectBaseModel):
    version: int = Field(..., description="نسخة المشروع (للتحقق من التعديل المتزامن)")
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class ChangeProjectStatusRequest(ProjectBaseModel):
    status: str = Field(..., description="الحالة الجديدة")
    reason: Optional[str] = None


class RecordExpenseRequest(ProjectBaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ المصروف")
    notes: Optional[str] = None
    reference: Optional[str] = None


class SetBudgetRequest(ProjectBaseModel):
    amount: Decimal = Field(..., ge=0, description="الميزانية الجديدة")
    currency: Optional[str] = "USD"


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/api/projects", response_model=ApiResponse)
async def create_project(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import CreateProjectCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateProjectCommand(
            name=request.name,
            code=request.code,
            description=request.description,
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            manager_id=request.manager_id,
            manager_name=request.manager_name,
            budget_amount=request.budget_amount,
            budget_currency=request.budget_currency or "USD",
            start_date=request.start_date.isoformat() if request.start_date else None,
            end_date=request.end_date.isoformat() if request.end_date else None,
            status=request.status or "planning",
            tags=request.tags,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء المشروع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/projects", response_model=ApiResponse)
async def list_projects(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    manager_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import ListProjectsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(ListProjectsQuery(
            status=status, search=search, customer_id=customer_id,
            manager_id=manager_id, limit=limit, offset=offset)) or []
        return ApiResponse(success=True, message="تم جلب المشاريع بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/projects/overview", response_model=ApiResponse)
async def get_projects_overview(
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import GetProjectOverviewQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        overview = query_bus.dispatch(GetProjectOverviewQuery())
        return ApiResponse(success=True, message="تم جلب إحصائيات المشاريع بنجاح", data=jsonable_encoder(overview))
    except Exception as e:
        logger.error(f"Error getting projects overview: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/projects/{project_id}", response_model=ApiResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import GetProjectQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetProjectQuery(project_id=project_id))
        if dto is None:
            return ApiResponse(success=False, message="المشروع غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب المشروع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting project: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/projects/{project_id}", response_model=ApiResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import UpdateProjectCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateProjectCommand(
            project_id=project_id,
            version=request.version,
            name=request.name,
            description=request.description,
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            manager_id=request.manager_id,
            manager_name=request.manager_name,
            start_date=request.start_date.isoformat() if request.start_date else None,
            end_date=request.end_date.isoformat() if request.end_date else None,
            tags=request.tags,
            updated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث المشروع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating project: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/projects/{project_id}", response_model=ApiResponse)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import DeleteProjectCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(DeleteProjectCommand(
            project_id=project_id, deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف المشروع بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error deleting project: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/projects/{project_id}/status", response_model=ApiResponse)
async def change_project_status(
    project_id: str,
    request: ChangeProjectStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import ChangeProjectStatusCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ChangeProjectStatusCommand(
            project_id=project_id, status=request.status, reason=request.reason,
            changed_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تغيير حالة المشروع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error changing project status: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/projects/{project_id}/expenses", response_model=ApiResponse)
async def record_project_expense(
    project_id: str,
    request: RecordExpenseRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import RecordProjectExpenseCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(RecordProjectExpenseCommand(
            project_id=project_id, amount=request.amount, notes=request.notes,
            reference=request.reference, recorded_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تسجيل المصروف بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error recording project expense: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/projects/{project_id}/budget", response_model=ApiResponse)
async def set_project_budget(
    project_id: str,
    request: SetBudgetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.projects.commands import SetProjectBudgetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SetProjectBudgetCommand(
            project_id=project_id, amount=request.amount,
            currency=request.currency or "USD", set_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعيين الميزانية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error setting project budget: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])