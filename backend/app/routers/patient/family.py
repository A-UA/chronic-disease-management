"""家属关联端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    FamilyServiceDep,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
)
from app.schemas.family import (
    FamilyLinkCreate,
    FamilyLinkRead,
    PatientProfileFamilyRead,
)

router = APIRouter()


@router.post("/links", response_model=FamilyLinkRead)
async def create_family_link(
    link_in: FamilyLinkCreate,
    service: FamilyServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """创建家属关联"""
    return await service.create_link(
        user_id=current_user.id,
        tenant_id=tenant_id,
        org_id=org_id,
        patient_id=link_in.patient_id,
        family_user_email=link_in.family_user_email,
        relationship_type=link_in.relationship_type,
        access_level=link_in.access_level,
    )


@router.get("/patients", response_model=list[FamilyLinkRead])
async def get_my_linked_patients(
    service: FamilyServiceDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """作为家属查看关联的患者列表"""
    return await service.get_my_linked_patients(current_user.id)


@router.get("/patients/{patient_id}", response_model=PatientProfileFamilyRead)
async def get_linked_patient_profile(
    patient_id: int,
    service: FamilyServiceDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """查看关联患者的档案"""
    return await service.get_linked_patient_profile(patient_id, current_user.id)


@router.delete("/links/{patient_id}")
async def unlink_family(
    patient_id: int,
    service: FamilyServiceDep,
    current_user: User = Depends(get_current_user),
):
    """家属解除与患者的关联"""
    await service.unlink(patient_id, current_user.id)
    return {"status": "ok"}
