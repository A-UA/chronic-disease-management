"""文档操作端点 — 纯 HTTP 适配层"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.models import User
from app.plugins.parser.base import DocumentParseError
from app.routers.deps import (
    DocumentRuntimeServiceDep,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
)
from app.schemas.document import DocumentRead

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/kb/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    service: DocumentRuntimeServiceDep,
    file: UploadFile = File(...),
    patient_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
):
    """上传文档入库"""
    try:
        return await service.upload_document(
            kb_id=kb_id, file=file, patient_id=patient_id,
            current_user=current_user, tenant_id=tenant_id, org_id=org_id
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("文档上传处理失败")
        raise HTTPException(status_code=500, detail="文档上传处理失败，请稍后重试")


@router.get("/kb/{kb_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    kb_id: int,
    service: DocumentRuntimeServiceDep,
    skip: int = 0,
    limit: int = 50,
    patient_id: int | None = None,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
):
    """列出当前知识库的文档"""
    return await service.list_documents(
        kb_id=kb_id, tenant_id=tenant_id, effective_org_id=effective_org_id,
        patient_id=patient_id, skip=skip, limit=limit
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    service: DocumentRuntimeServiceDep,
    tenant_id: int = Depends(inject_rls_context),
):
    """获取指定文档详细信息"""
    return await service.get_document(document_id=document_id, tenant_id=tenant_id)


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    service: DocumentRuntimeServiceDep,
    tenant_id: int = Depends(inject_rls_context),
):
    """删除文档（附带清洗软删）"""
    return await service.delete_document(document_id=document_id, tenant_id=tenant_id)


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    service: DocumentRuntimeServiceDep,
    tenant_id: int = Depends(inject_rls_context),
):
    """查看入库状态"""
    return await service.get_document_status(document_id=document_id, tenant_id=tenant_id)
