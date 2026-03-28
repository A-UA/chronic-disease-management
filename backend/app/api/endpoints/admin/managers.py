from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.api.deps import get_db, get_current_org, check_permission
from app.db.models import (
    ManagerProfile,
    PatientManagerAssignment,
    PatientProfile,
    OrganizationUser,
    User,
)
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class ManagerRead(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    bio: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ManagerDetailRead(ManagerRead):
    email: str | None = None
    name: str | None = None
    assigned_patient_count: int = 0


class AssignmentCreate(BaseModel):
    patient_id: int
    manager_id: int
    assignment_role: str = "main"


class AssignmentRead(BaseModel):
    manager_id: int
    patient_id: int
    assignment_role: str
    patient_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[ManagerDetailRead])
async def list_managers(
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("patient:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ManagerProfile)
        .options(selectinload(ManagerProfile.user))
        .where(ManagerProfile.org_id == org_id)
    )
    result = await db.execute(stmt)
    managers = result.scalars().all()

    reads = []
    for m in managers:
        count_stmt = select(PatientManagerAssignment).where(
            PatientManagerAssignment.manager_id == m.user_id
        )
        assignments = (await db.execute(count_stmt)).scalars().all()
        reads.append(
            ManagerDetailRead(
                id=m.id,
                user_id=m.user_id,
                title=m.title,
                bio=m.bio,
                is_active=m.is_active,
                email=m.user.email,
                name=m.user.name,
                assigned_patient_count=len(assignments),
            )
        )
    return reads


@router.get("/{manager_id}/patients", response_model=List[AssignmentRead])
async def get_manager_patients(
    manager_id: int,
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("patient:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PatientManagerAssignment)
        .options(selectinload(PatientManagerAssignment.patient))
        .where(
            PatientManagerAssignment.manager_id == manager_id,
            PatientManagerAssignment.org_id == org_id,
        )
    )
    result = await db.execute(stmt)
    assignments = result.scalars().all()
    return [
        AssignmentRead(
            manager_id=a.manager_id,
            patient_id=a.patient_id,
            assignment_role=a.assignment_role,
            patient_name=a.patient.real_name if a.patient else None,
        )
        for a in assignments
    ]


@router.post("/assignments")
async def create_assignment(
    data: AssignmentCreate,
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("org:manage_members")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.dialects.postgresql import insert

    stmt = (
        insert(PatientManagerAssignment)
        .values(
            org_id=org_id,
            manager_id=data.manager_id,
            patient_id=data.patient_id,
            assignment_role=data.assignment_role,
        )
        .on_conflict_do_update(
            index_elements=["manager_id", "patient_id"],
            set_={"assignment_role": data.assignment_role},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}
