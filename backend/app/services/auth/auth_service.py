"""认证业务服务"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import security
from app.base.config import settings
from app.base.exceptions import ForbiddenError, ValidationError
from app.models import (
    Organization,
    OrganizationUser,
    OrganizationUserRole,
    PasswordResetToken,
    Role,
    Tenant,
    User,
)
from app.repositories.auth_repo import AuthRepository, PasswordResetTokenRepository
from app.repositories.menu_repo import MenuRepository
from app.repositories.org_repo import OrganizationRepository
from app.repositories.org_user_repo import (
    OrganizationUserRepository,
    OrganizationUserRoleRepository,
)
from app.repositories.role_repo import PermissionRepository, RoleRepository
from app.repositories.tenant_repo import TenantRepository
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserRead
from app.services.auth.email import send_reset_code_email
from app.services.system.rbac import RBACService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.org_user_repo = OrganizationUserRepository(db)
        self.org_user_role_repo = OrganizationUserRoleRepository(db)
        self.role_repo = RoleRepository(db)
        self.menu_repo = MenuRepository(db)
        self.auth_repo = AuthRepository(db)
        self.pwd_repo = PasswordResetTokenRepository(db)
        self.perm_repo = PermissionRepository(db)

    async def register(self, *, email: str, password: str, name: str | None) -> dict:
        """注册并创建默认租户+组织"""
        if await self.user_repo.get_by_email(email):
            raise ValidationError("The user with this email already exists.")

        user = User(
            email=email,
            password_hash=security.get_password_hash(password),
            name=name,
        )
        await self.user_repo.create(user)

        tenant = Tenant(
            name=f"{user.name or user.email}'s Workspace",
            slug=f"ws-{user.id}",
            plan_type="free",
        )
        await self.tenant_repo.create(tenant)

        org = Organization(tenant_id=tenant.id, name="默认部门", code="DEFAULT")
        await self.org_repo.create(org)

        org_user = OrganizationUser(
            tenant_id=tenant.id, org_id=org.id, user_id=user.id
        )
        await self.org_user_repo.create(org_user)


        stmt_role = select(Role).where(Role.code == "owner", Role.tenant_id.is_(None))
        r_owner = (await self.db.execute(stmt_role)).scalar_one_or_none()
        if r_owner:
            await self.org_user_role_repo.create(
                OrganizationUserRole(
                    tenant_id=tenant.id, org_id=org.id, user_id=user.id, role_id=r_owner.id
                )
            )

        user_count = await self.user_repo.count()
        if user_count == 1:
            stmt_pa = select(Role).where(Role.code == "platform_admin", Role.tenant_id.is_(None))
            pa_role = (await self.db.execute(stmt_pa)).scalar_one_or_none()
            if pa_role:
                await self.org_user_role_repo.create(
                    OrganizationUserRole(
                        tenant_id=tenant.id, org_id=org.id, user_id=user.id, role_id=pa_role.id
                    )
                )

        await self.db.commit()
        await self.db.refresh(user)
        return {"id": user.id, "email": user.email, "tenant_id": tenant.id, "org_id": org.id}

    async def login(self, *, username: str, password: str) -> dict:
        """登录（含多部门选择）"""
        user = await self.user_repo.get_by_email(username)
        if not user or not security.verify_password(password, user.password_hash):
            raise ValidationError("Incorrect email or password")

        org_users = await self.auth_repo.get_user_orgs_with_tenant(user.id)
        if len(org_users) == 0:
            raise ValidationError("User is not a member of any active organization")

        if len(org_users) == 1:
            ou = org_users[0]
            org = ou.organization
            role_codes = [r.code for r in ou.rbac_roles]
            token = security.create_access_token(
                user.id,
                tenant_id=org.tenant_id,
                org_id=org.id,
                roles=role_codes,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            )
            return {
                "access_token": token,
                "token_type": "bearer",
                "organization": {"id": org.id, "name": org.name, "tenant_id": org.tenant_id},
                "require_org_selection": False,
            }

        selection_token = security.create_selection_token(user.id)
        org_list = [
            {
                "id": ou.organization.id,
                "name": ou.organization.name,
                "tenant_id": ou.organization.tenant_id,
                "tenant_name": getattr(ou.organization.tenant, "name", None) if hasattr(ou.organization, "tenant") else None,
            }
            for ou in org_users
        ]
        return {
            "access_token": None,
            "token_type": "bearer",
            "organizations": org_list,
            "require_org_selection": True,
            "selection_token": selection_token,
        }

    async def select_org(self, *, org_id: int, selection_token: str) -> dict:
        """选择部门签发 JWT"""
        try:
            payload = pyjwt.decode(
                selection_token, settings.JWT_SECRET, algorithms=[security.ALGORITHM]
            )
            if payload.get("purpose") != "org_selection":
                raise ValidationError("Invalid selection token")
            user_id = int(payload["sub"])
        except pyjwt.PyJWTError:
            raise ValidationError("Invalid or expired selection token")

        ou = await self.auth_repo.get_org_user_with_roles(user_id, org_id)
        if not ou:
            raise ForbiddenError("User is not a member of this organization")

        org = await self.org_repo.get_by_id(org_id)
        role_codes = [r.code for r in ou.rbac_roles]
        token = security.create_access_token(
            user_id,
            tenant_id=org.tenant_id,
            org_id=org.id,
            roles=role_codes,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "organization": {"id": org.id, "name": org.name, "tenant_id": org.tenant_id},
        }

    async def switch_org(self, *, user_id: int, org_id: int) -> dict:
        """切换部门"""
        ou = await self.auth_repo.get_org_user_with_roles(user_id, org_id)
        if not ou:
            raise ForbiddenError("User is not a member of this organization")

        org = await self.org_repo.get_by_id(org_id)
        role_codes = [r.code for r in ou.rbac_roles]
        token = security.create_access_token(
            user_id,
            tenant_id=org.tenant_id,
            org_id=org.id,
            roles=role_codes,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "organization": {"id": org.id, "name": org.name, "tenant_id": org.tenant_id},
        }

    async def list_my_orgs(self, user_id: int) -> list[dict]:
        """当前用户可用部门列表"""
        org_users = await self.auth_repo.get_user_orgs_with_tenant(user_id)
        return [
            {"id": ou.organization.id, "name": ou.organization.name, "tenant_id": ou.organization.tenant_id}
            for ou in org_users
        ]

    async def get_me(self, *, user: User, org_id: int, tenant_id: int) -> dict:
        """当前用户信息 + 权限"""
        user_data = UserRead.model_validate(user)
        user_data.org_id = org_id
        user_data.tenant_id = tenant_id

        org_user = await self.auth_repo.get_org_user_with_roles(user.id, org_id)
        if org_user and org_user.rbac_roles:
            role_ids = [r.id for r in org_user.rbac_roles]
            user_data.permissions = list(
                await RBACService.get_effective_permissions(self.db, role_ids)
            )
        else:
            user_data.permissions = []

        return user_data

    async def get_menu_tree(
        self, *, org_user: OrganizationUser, tenant_id: int
    ) -> list[dict]:
        role_ids = [r.id for r in org_user.rbac_roles]
        all_role_ids = await self.role_repo.get_all_role_ids(role_ids)
        user_perm_codes = await self.perm_repo.get_codes_by_role_ids(list(all_role_ids))
        all_menus = await self.menu_repo.list_active(tenant_id)

        visible_menus = [
            m for m in all_menus if not m.permission_code or m.permission_code in user_perm_codes
        ]

        menu_map = {}
        for m in visible_menus:
            menu_map[m.id] = {
                "id": m.id, "name": m.name, "code": m.code, "menu_type": m.menu_type,
                "path": m.path, "icon": m.icon, "permission_code": m.permission_code,
                "sort": m.sort, "is_visible": m.is_visible, "is_enabled": m.is_enabled,
                "meta": m.meta, "children": [],
            }
        roots = []
        visible_ids = {m.id for m in visible_menus}
        for m in visible_menus:
            node = menu_map[m.id]
            if m.parent_id and m.parent_id in visible_ids:
                menu_map[m.parent_id]["children"].append(node)
            else:
                roots.append(node)

        def prune(items):
            return [
                item for item in items
                if item["menu_type"] != "directory" or len(item.get("children", [])) > 0
            ]

        return prune(roots)

    async def update_password(
        self, *, user: User, current_password: str, new_password: str
    ) -> dict:
        """修改密码"""
        if not security.verify_password(current_password, user.password_hash):
            raise ValidationError("Incorrect current password")
        await self.user_repo.update(user, {"password_hash": security.get_password_hash(new_password)})
        await self.db.commit()
        return {"message": "Password updated successfully"}

    async def update_profile(self, *, user: User, data: dict) -> dict:
        """修改用户基本信息"""
        await self.user_repo.update(user, data)
        await self.db.commit()
        return {"status": "ok", "name": user.name}

    async def forgot_password(self, email: str) -> dict:
        """请求密码重置"""
        user = await self.user_repo.get_by_email(email)
        if user:
            code = f"{secrets.randbelow(1000000):06d}"
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            token = PasswordResetToken(user_id=user.id, token=code, expires_at=expires_at)
            await self.pwd_repo.create(token)
            await self.db.commit()

            await send_reset_code_email(email, code)

        return {"message": "If the email exists, a reset code has been sent."}

    async def reset_password(self, *, email: str, code: str, new_password: str) -> dict:
        """使用验证码重置密码"""
        reset_token = await self.pwd_repo.get_valid_token(email, code)
        if not reset_token:
            raise ValidationError("Invalid or expired reset code")

        now = datetime.now(timezone.utc)
        expires = (
            reset_token.expires_at.replace(tzinfo=timezone.utc)
            if reset_token.expires_at.tzinfo is None
            else reset_token.expires_at
        )
        if expires < now:
            raise ValidationError("Reset code has expired")

        user = await self.db.get(User, reset_token.user_id)
        await self.user_repo.update(user, {"password_hash": security.get_password_hash(new_password)})
        await self.pwd_repo.update(reset_token, {"used": True})
        await self.db.commit()
        return {"message": "Password has been reset successfully"}
