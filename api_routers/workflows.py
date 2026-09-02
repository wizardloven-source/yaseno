from decimal import Decimal
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user

router = APIRouter(prefix="", tags=["workflows"])


# =============================================================================
# FIXED ASSETS ENDPOINTS - نقاط نهاية الأصول الثابتة
# =============================================================================


class CreateFixedAssetRequest(BaseModel):
    code: str
    name: str
    acquisition_cost: Decimal
    acquisition_date: date
    asset_type: str = "other"
    useful_life_years: int = 5
    salvage_value: Decimal = Decimal('0')
    depreciation_method: str = "straight_line"
    currency: str = "USD"
    category: Optional[str] = None
    location: Optional[str] = None
    responsible_person: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    notes: Optional[str] = None


class PostDepreciationRequest(BaseModel):
    period: int


class DisposeFixedAssetRequest(BaseModel):
    disposal_date: date
    disposal_method: str = "sale"
    sale_amount: Optional[Decimal] = None
    scrap_value: Optional[Decimal] = None
    reason: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class RunMonthlyDepreciationRequest(BaseModel):
    as_of_date: Optional[date] = None


@router.post("/api/assets", response_model=ApiResponse)
async def create_fixed_asset(
    request: CreateFixedAssetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import CreateFixedAssetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateFixedAssetCommand(
            code=request.code,
            name=request.name,
            acquisition_cost=request.acquisition_cost,
            acquisition_date=request.acquisition_date,
            asset_type=request.asset_type,
            useful_life_years=request.useful_life_years,
            salvage_value=request.salvage_value,
            depreciation_method=request.depreciation_method,
            currency=request.currency,
            category=request.category,
            location=request.location,
            responsible_person=request.responsible_person,
            supplier_id=request.supplier_id,
            supplier_name=request.supplier_name,
            serial_number=request.serial_number,
            barcode=request.barcode,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء الأصل الثابت بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating fixed asset: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/assets", response_model=ApiResponse)
async def list_fixed_assets(
    asset_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.queries import ListFixedAssetsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(ListFixedAssetsQuery(
            asset_type=asset_type, status=status,
            include_inactive=include_inactive, limit=limit, offset=offset))
        return ApiResponse(success=True, message="تم جلب الأصول الثابتة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error listing fixed assets: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/assets/{asset_id}", response_model=ApiResponse)
async def get_fixed_asset(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.queries import GetFixedAssetQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetFixedAssetQuery(asset_id=asset_id))
        if data is None:
            return ApiResponse(success=False, message="الأصل الثابت غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب الأصل الثابت بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting fixed asset: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/assets/run-depreciation", response_model=ApiResponse)
async def run_monthly_depreciation(
    request: RunMonthlyDepreciationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import RunMonthlyDepreciationCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(RunMonthlyDepreciationCommand(
            as_of_date=request.as_of_date, posted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تشغيل الإهلاك الشهري بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error running monthly depreciation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/assets/{asset_id}/depreciation", response_model=ApiResponse)
async def post_depreciation(
    asset_id: str,
    request: PostDepreciationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import PostDepreciationCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(PostDepreciationCommand(
            asset_id=asset_id, period=request.period, posted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم ترحيل الإهلاك بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error posting depreciation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/assets/{asset_id}/dispose", response_model=ApiResponse)
async def dispose_fixed_asset(
    asset_id: str,
    request: DisposeFixedAssetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import DisposeFixedAssetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(DisposeFixedAssetCommand(
            asset_id=asset_id,
            disposal_date=request.disposal_date,
            disposal_method=request.disposal_method,
            sale_amount=request.sale_amount,
            scrap_value=request.scrap_value,
            reason=request.reason,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            disposed_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم التصرف في الأصل الثابت بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error disposing fixed asset: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# WORKFLOW ENDPOINTS - نقاط نهاية سير العمل والموافقات
# =============================================================================


class WorkflowStepRequest(BaseModel):
    name: str
    order: int = 0
    role: str = ""
    required_approvals: int = 1
    requires_all: bool = False
    is_final: bool = False
    timeout_hours: Optional[int] = None
    escalation_role: Optional[str] = None
    description: Optional[str] = None


class CreateWorkflowRequest(BaseModel):
    name: str
    code: str
    entity_type: str
    steps: List[WorkflowStepRequest]
    description: Optional[str] = None
    is_mandatory: bool = False
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None


class CreateApprovalRequestRequest(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    priority: str = "normal"
    due_date: Optional[datetime] = None
    entity_data: Optional[Dict[str, Any]] = None


class ApproveRequestRequest(BaseModel):
    approver_id: str
    approver_name: str = ""
    comment: Optional[str] = None


class RejectRequestRequest(BaseModel):
    approver_id: str
    approver_name: str = ""
    reason: str = ""


class ActionRequestRequest(BaseModel):
    reason: Optional[str] = None


class ReassignRequestRequest(BaseModel):
    new_approver_id: str
    new_approver_name: Optional[str] = None
    reason: Optional[str] = None


class BatchRequestsRequest(BaseModel):
    request_ids: List[str]
    comment: Optional[str] = None
    reason: Optional[str] = None


@router.post("/api/workflows", response_model=ApiResponse)
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import CreateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CreateWorkflowCommand(
            name=request.name,
            code=request.code,
            entity_type=request.entity_type,
            steps=[s.model_dump() for s in request.steps],
            description=request.description,
            is_mandatory=request.is_mandatory,
            auto_approve_threshold=request.auto_approve_threshold,
            auto_approve_after_days=request.auto_approve_after_days,
            created_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم إنشاء سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/workflows", response_model=ApiResponse)
async def list_workflows(
    entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ListWorkflowsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(ListWorkflowsQuery(
            entity_type=entity_type, status=status, limit=limit, offset=offset))
        return ApiResponse(success=True, message="تم جلب سير العمل بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/workflows/by-entity/{entity_type}", response_model=ApiResponse)
async def get_workflow_by_entity(
    entity_type: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetWorkflowByEntityQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetWorkflowByEntityQuery(entity_type=entity_type))
        if data is None:
            return ApiResponse(success=False, message="لا يوجد سير عمل لهذا الكيان", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب سير العمل بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting workflow by entity: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/workflows/{workflow_id}", response_model=ApiResponse)
async def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetWorkflowQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetWorkflowQuery(workflow_id=workflow_id))
        if data is None:
            return ApiResponse(success=False, message="سير العمل غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب سير العمل بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/workflows/{workflow_id}", response_model=ApiResponse)
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import UpdateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(UpdateWorkflowCommand(
            workflow_id=workflow_id,
            name=request.name,
            description=request.description,
            is_mandatory=request.is_mandatory,
            auto_approve_threshold=request.auto_approve_threshold,
            auto_approve_after_days=request.auto_approve_after_days,
            updated_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم تحديث سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/workflows/{workflow_id}/activate", response_model=ApiResponse)
async def activate_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ActivateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ActivateWorkflowCommand(
            workflow_id=workflow_id, activated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تفعيل سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error activating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/workflows/{workflow_id}/deactivate", response_model=ApiResponse)
async def deactivate_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import DeactivateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(DeactivateWorkflowCommand(
            workflow_id=workflow_id, deactivated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعطيل سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error deactivating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/workflows/{workflow_id}", response_model=ApiResponse)
async def delete_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import DeleteWorkflowCommand
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(DeleteWorkflowCommand(
            workflow_id=workflow_id, deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف سير العمل بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests", response_model=ApiResponse)
async def create_approval_request(
    request: CreateApprovalRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import CreateApprovalRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CreateApprovalRequestCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            title=request.title,
            description=request.description,
            amount=request.amount,
            currency=request.currency,
            priority=request.priority,
            due_date=request.due_date,
            entity_data=request.entity_data,
            created_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم إنشاء طلب الموافقة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating approval request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/approval-requests/pending", response_model=ApiResponse)
async def list_pending_requests(
    entity_type: Optional[str] = Query(None),
    approver_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ListPendingRequestsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(ListPendingRequestsQuery(
            entity_type=entity_type, approver_id=approver_id, limit=limit, offset=offset))
        return ApiResponse(success=True, message="تم جلب الطلبات المعلقة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error listing pending requests: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/approval-requests/statistics", response_model=ApiResponse)
async def get_request_statistics(
    entity_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetRequestStatisticsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetRequestStatisticsQuery(entity_type=entity_type))
        return ApiResponse(success=True, message="تم جلب إحصائيات الطلبات بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting request statistics: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/batch-approve", response_model=ApiResponse)
async def batch_approve_requests(
    request: BatchRequestsRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import BatchApproveRequestsCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(BatchApproveRequestsCommand(
            request_ids=request.request_ids, comment=request.comment, approved_by=current_user["username"]))
        return ApiResponse(success=True, message="تمت الموافقة الجماعية بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error batch approving requests: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/batch-reject", response_model=ApiResponse)
async def batch_reject_requests(
    request: BatchRequestsRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import BatchRejectRequestsCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(BatchRejectRequestsCommand(
            request_ids=request.request_ids, reason=request.reason or "", rejected_by=current_user["username"]))
        return ApiResponse(success=True, message="تم الرفض الجماعي بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error batch rejecting requests: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/approval-requests/{request_id}", response_model=ApiResponse)
async def get_approval_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetRequestQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetRequestQuery(request_id=request_id))
        if data is None:
            return ApiResponse(success=False, message="طلب الموافقة غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب طلب الموافقة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting approval request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/{request_id}/submit", response_model=ApiResponse)
async def submit_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import SubmitRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SubmitRequestCommand(
            request_id=request_id, submitted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تقديم الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error submitting request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/{request_id}/approve", response_model=ApiResponse)
async def approve_request(
    request_id: str,
    request: ApproveRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ApproveRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ApproveRequestCommand(
            request_id=request_id,
            approver_id=request.approver_id or current_user["username"],
            approver_name=request.approver_name,
            comment=request.comment,
        ))
        return ApiResponse(success=True, message="تمت الموافقة على الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error approving request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/{request_id}/reject", response_model=ApiResponse)
async def reject_request(
    request_id: str,
    request: RejectRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import RejectRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(RejectRequestCommand(
            request_id=request_id,
            approver_id=request.approver_id or current_user["username"],
            approver_name=request.approver_name,
            reason=request.reason,
        ))
        return ApiResponse(success=True, message="تم رفض الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error rejecting request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/{request_id}/cancel", response_model=ApiResponse)
async def cancel_request(
    request_id: str,
    request: ActionRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import CancelRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CancelRequestCommand(
            request_id=request_id, cancelled_by=current_user["username"], reason=request.reason))
        return ApiResponse(success=True, message="تم إلغاء الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error cancelling request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/{request_id}/escalate", response_model=ApiResponse)
async def escalate_request(
    request_id: str,
    request: ActionRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import EscalateRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(EscalateRequestCommand(
            request_id=request_id, escalated_by=current_user["username"], reason=request.reason))
        return ApiResponse(success=True, message="تم تصعيد الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error escalating request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/approval-requests/{request_id}/reassign", response_model=ApiResponse)
async def reassign_request(
    request_id: str,
    request: ReassignRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ReassignRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ReassignRequestCommand(
            request_id=request_id,
            new_approver_id=request.new_approver_id,
            new_approver_name=request.new_approver_name,
            reason=request.reason,
            reassigned_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تمت إعادة تعيين الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error reassigning request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
