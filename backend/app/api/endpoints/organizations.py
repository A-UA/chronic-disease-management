from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sqlalchemy import delete
import secrets
from datetime import datetime, timedelta, timezone

from app.api.deps import get_db, get_current_user, check_permission, get_current_org_id, get_current_tenant_id
from app.db.models import Organization, OrganizationUser, OrganizationUserRole, User, Role, OrganizationInvitation
from app.schemas.organization import (
    OrganizationReadAdmin, 
    OrganizationCreate, 
    OrganizationUpdate,
    OrganizationMemberRead,
    OrganizationInvitationCreate,
    OrganizationInvitationRead
)

router = APIRouter()

@router.get("/me", response_model=List[OrganizationReadAdmin])
async def get_my_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[通用] 获取当前用户所属的所有机构"""
    stmt = (
        select(Organization)
        .join(OrganizationUser)
        .where(OrganizationUser.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("", response_model=List[OrganizationReadAdmin])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    _permission=Depends(check_permission("platform:manage")), # 仅限平台级角色
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 列出系统所有机构"""
    stmt = select(Organization).offset(skip).limit(limit)
    if search:
        stmt = stmt.where(Organization.name.ilike(f"%{search}%"))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=OrganizationReadAdmin)
async def create_organization(
    org_in: OrganizationCreate,
    _permission=Depends(check_permission("platform:manage")),
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 创建新机构"""
    org = Organization(name=org_in.name, plan_type=org_in.plan_type)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.put("/{org_id}", response_model=OrganizationReadAdmin)
async def update_organization(
    org_id: int,
    org_in: OrganizationUpdate,
    org_id_header: int = Depends(get_current_org_id),
    _permission=Depends(check_permission("org:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理视图] 编辑机构信息"""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in org_in.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return org


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    _permission=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 删除组织（检查成员关联）"""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 检查组织下是否还有成员
    from sqlalchemy import func as sqlfunc
    member_count = (await db.execute(
        select(sqlfunc.count()).where(OrganizationUser.org_id == org_id)
    )).scalar() or 0
    if member_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Organization still has {member_count} member(s). Remove them first.",
        )

    await db.delete(org)
    await db.commit()
    return {"status": "ok"}


@router.get("/{org_id}/members", response_model=List[OrganizationMemberRead])
async def get_organization_members(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[管理视图] 获取机构成员列表 (含角色)"""
    # 校验是否是该机构成员或平台管理员
    stmt_check = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id
    )
    is_member = (await db.execute(stmt_check)).scalar_one_or_none()

    if not is_member:
        # 检查是否是平台管理员
        stmt_platform = (
            select(OrganizationUserRole)
            .join(Role, Role.id == OrganizationUserRole.role_id)
            .where(
                OrganizationUserRole.user_id == current_user.id,
                Role.code.in_(["platform_admin", "platform_viewer"]),
                Role.tenant_id.is_(None),
            )
        )
        if not (await db.execute(stmt_platform)).scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized")

    stmt = (
        select(OrganizationUser)
        .options(
            selectinload(OrganizationUser.user),
            selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
        )
        .where(OrganizationUser.org_id == org_id)
    )
    result = await db.execute(stmt)
    members = []
    for org_user in result.scalars().all():
        members.append({
            "user_id": org_user.user.id,
            "email": org_user.user.email,
            "name": org_user.user.name,
            "roles": [r.code for r in org_user.rbac_roles],
            "user_type": org_user.user_type,
        })
    return members

@router.delete("/{org_id}/members/{user_id}", response_model=dict)
async def remove_organization_member(
    org_id: int,
    user_id: int,
    _org_member=Depends(check_permission("org:manage")),
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 移除机构成员"""
    # 不能移除最后一名成员的保护逻辑（可选），或直接删除关联
    stmt = delete(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == user_id
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Member not found in organization")
    await db.commit()
    return {"message": "Member removed successfully"}

@router.get("/{org_id}/invitations", response_model=List[OrganizationInvitationRead])
async def list_invitations(
    org_id: int,
    _org_member=Depends(check_permission("org:manage")),
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 列出机构的待处理邀请"""
    stmt = select(OrganizationInvitation).where(
        OrganizationInvitation.org_id == org_id,
        OrganizationInvitation.status == "pending"
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{org_id}/invitations", response_model=OrganizationInvitationRead)
async def create_invitation(
    org_id: int,
    invitation_in: OrganizationInvitationCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    _org_member=Depends(check_permission("org:manage")),
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 发起组织邀请"""
    # 检查目标用户是否已经是组织成员
    user_stmt = select(User).where(User.email == invitation_in.email)
    target_user = (await db.execute(user_stmt)).scalar_one_or_none()
    
    if target_user:
        member_stmt = select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == target_user.id
        )
        if (await db.execute(member_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a member")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    invitation = OrganizationInvitation(
        tenant_id=tenant_id,
        org_id=org_id,
        inviter_id=current_user.id,
        email=invitation_in.email,
        role=invitation_in.role,
        token=token,
        status="pending",
        expires_at=expires_at
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation

@router.post("/invitations/{token}/accept", response_model=dict)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """[通用] 接受组织邀请"""
    stmt = select(OrganizationInvitation).where(
        OrganizationInvitation.token == token,
        OrganizationInvitation.status == "pending"
    )
    invitation = (await db.execute(stmt)).scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation token")
        
    # Python 的 naive datetime 和 current_user 兼容处理
    if invitation.expires_at.tzinfo is None:
        now = datetime.utcnow()
    else:
        now = datetime.now(timezone.utc)
        
    if invitation.expires_at < now:
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")
        
    if current_user.email != invitation.email:
        raise HTTPException(status_code=403, detail="Invitation is for another email address")

    # 查找邀请对应的组织以获取 tenant_id
    org = await db.get(Organization, invitation.org_id)
    t_id = org.tenant_id if org else None

    # 创建组织成员关联
    org_user = OrganizationUser(
        tenant_id=t_id,
        org_id=invitation.org_id,
        user_id=current_user.id,
        user_type="staff"
    )
    db.add(org_user)
    
    # 查找邀请指定的角色
    role_stmt = select(Role).where(
        Role.code == invitation.role,
        Role.tenant_id == t_id
    )
    role = (await db.execute(role_stmt)).scalar_one_or_none()
    
    # 回退到找系统级角色
    if not role:
        sys_role_stmt = select(Role).where(
            Role.code == invitation.role,
            Role.tenant_id.is_(None)
        )
        role = (await db.execute(sys_role_stmt)).scalar_one_or_none()

    if role:
        user_role = OrganizationUserRole(
            tenant_id=t_id,
            org_id=invitation.org_id,
            user_id=current_user.id,
            role_id=role.id
        )
        db.add(user_role)

    invitation.status = "accepted"
    await db.commit()
    return {"message": "You have joined the organization successfully"}
