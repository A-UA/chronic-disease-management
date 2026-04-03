from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.api.deps import get_db, get_current_org, check_permission, check_org_admin
from app.db.models import Role, Permission, Resource, Action, RoleConstraint, OrganizationUserRole, OrganizationUser
from app.schemas.rbac import RoleRead, PermissionRead, RoleCreate
from app.services.rbac import RBACService
from app.services.audit import audit_action

router = APIRouter()

@router.get("/resources", response_model=List[dict])
async def list_resources(
    _org_admin=Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 获取系统受保护资源字典"""
    stmt = select(Resource)
    result = await db.execute(stmt)
    return [{"id": r.id, "name": r.name, "code": r.code} for r in result.scalars().all()]

@router.get("/actions", response_model=List[dict])
async def list_actions(
    _org_admin=Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 获取系统操作行为字典"""
    stmt = select(Action)
    result = await db.execute(stmt)
    return [{"id": a.id, "name": a.name, "code": a.code} for a in result.scalars().all()]

@router.get("/roles", response_model=List[RoleRead])
async def list_roles(
    org_id: int = Depends(get_current_org),
    _org_admin=Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """获取本组织可用角色列表"""
    stmt = (
        select(Role)
        .options(selectinload(Role.permissions))
        .where((Role.org_id == org_id) | (Role.org_id.is_(None)))
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/roles", response_model=RoleRead)
async def create_custom_role(
    role_in: RoleCreate,
    org_id: int = Depends(get_current_org),
    org_admin: OrganizationUser = Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 创建组织自定义角色 (支持继承)"""
    # 1. Check if code exists in org
    stmt = select(Role).where(Role.org_id == org_id, Role.code == role_in.code)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role code already exists in this organization")

    # 2. Verify parent role visibility
    if role_in.parent_role_id:
        parent = await db.get(Role, role_in.parent_role_id)
        if not parent or (parent.org_id is not None and parent.org_id != org_id):
            raise HTTPException(status_code=400, detail="Invalid parent role")

    # 3. Create Role
    role = Role(
        org_id=org_id,
        name=role_in.name,
        code=role_in.code,
        description=role_in.description,
        parent_role_id=role_in.parent_role_id,
        is_system=False
    )
    
    # 4. Attach Direct Permissions
    if role_in.permission_ids:
        stmt_p = select(Permission).where(Permission.id.in_(role_in.permission_ids))
        perms = (await db.execute(stmt_p)).scalars().all()
        role.permissions = list(perms)

    db.add(role)
    await db.flush() # Get role.id
    
    # Audit log
    await audit_action(
        db,
        user_id=org_admin.user_id,
        org_id=org_id,
        action="CREATE_ROLE",
        resource_type="role",
        resource_id=role.id,
        details=f"Created custom role: {role.code}"
    )

    await db.commit()
    await db.refresh(role, ["permissions"])
    return role

@router.post("/members/{user_id}/roles")
async def assign_user_roles(
    user_id: int,
    role_ids: List[int],
    org_id: int = Depends(get_current_org),
    org_admin: OrganizationUser = Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 为组织成员授权，包含 SSD 约束校验"""
    # 1. Verify roles belong to org/system
    stmt_v = select(Role).where(
        Role.id.in_(role_ids),
        (Role.org_id == org_id) | (Role.org_id.is_(None))
    )
    valid_roles = (await db.execute(stmt_v)).scalars().all()
    if len(valid_roles) != len(role_ids):
        raise HTTPException(status_code=400, detail="One or more roles are invalid for this organization")

    # 2. SSD Constraint Check (Static Separation of Duties)
    conflict_msg = await RBACService.check_ssd_violation(db, org_id, role_ids)
    if conflict_msg:
        raise HTTPException(status_code=400, detail=conflict_msg)

    # 3. Update roles
    # Clean old ones first
    from app.db.models import OrganizationUserRole
    stmt_del = select(OrganizationUserRole).where(
        OrganizationUserRole.org_id == org_id,
        OrganizationUserRole.user_id == user_id
    )
    old_links = (await db.execute(stmt_del)).scalars().all()
    for link in old_links:
        await db.delete(link)
    
    # Add new ones
    for rid in role_ids:
        db.add(OrganizationUserRole(org_id=org_id, user_id=user_id, role_id=rid))
    
    # Audit log
    await audit_action(
        db,
        user_id=org_admin.user_id,
        org_id=org_id,
        action="ASSIGN_ROLES",
        resource_type="user",
        resource_id=user_id,
        details=f"Assigned roles {role_ids} to user {user_id}"
    )
    
    await db.commit()
    return {"status": "ok", "assigned_roles": [r.code for r in valid_roles]}


# ── Role 更新/删除 ──

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    org_id: int = Depends(get_current_org),
    org_admin: OrganizationUser = Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 更新自定义角色"""
    role = await db.get(Role, role_id)
    if not role or role.org_id != org_id:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system roles")

    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.permission_ids is not None:
        stmt = select(Permission).where(Permission.id.in_(data.permission_ids))
        perms = (await db.execute(stmt)).scalars().all()
        role.permissions = list(perms)

    await db.commit()
    await db.refresh(role, ["permissions"])
    return {
        "id": role.id, "name": role.name, "code": role.code,
        "description": role.description, "is_system": role.is_system,
    }


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    org_id: int = Depends(get_current_org),
    org_admin: OrganizationUser = Depends(check_org_admin()),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 删除自定义角色（检查绑定用户）"""
    role = await db.get(Role, role_id)
    if not role or role.org_id != org_id:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system roles")

    # 检查是否有用户绑定该角色
    bound_stmt = select(OrganizationUserRole).where(
        OrganizationUserRole.role_id == role_id
    )
    bound = (await db.execute(bound_stmt)).scalars().first()
    if bound:
        raise HTTPException(
            status_code=409,
            detail="Role is still assigned to users. Unassign first."
        )

    await db.delete(role)
    await db.commit()
    return {"status": "ok"}
