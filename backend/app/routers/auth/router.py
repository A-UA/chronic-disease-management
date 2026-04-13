"""认证端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.models import OrganizationUser, User
from app.routers.deps import (
    AuthServiceDep,
    get_current_org_id,
    get_current_org_user,
    get_current_roles,
    get_current_tenant_id,
    get_current_user,
)
from app.schemas.user import UserCreate, UserRead, UserUpdatePassword

router = APIRouter()


class SelectOrgRequest(BaseModel):
    org_id: int
    selection_token: str


class SwitchOrgRequest(BaseModel):
    org_id: int


class UserProfileUpdate(BaseModel):
    name: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


@router.post("/register", response_model=Any)
async def register(user_in: UserCreate, service: AuthServiceDep) -> Any:
    """注册"""
    return await service.register(email=user_in.email, password=user_in.password, name=user_in.name)


@router.post("/login/access-token")
async def login_access_token(
    service: AuthServiceDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """登录（含多部门选择）"""
    return await service.login(username=form_data.username, password=form_data.password)


@router.post("/select-org")
async def select_org(data: SelectOrgRequest, service: AuthServiceDep) -> Any:
    """登录后选择部门"""
    return await service.select_org(org_id=data.org_id, selection_token=data.selection_token)


@router.post("/switch-org")
async def switch_org(
    data: SwitchOrgRequest,
    service: AuthServiceDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """已登录用户切换部门"""
    return await service.switch_org(user_id=current_user.id, org_id=data.org_id)


@router.get("/my-orgs")
async def list_my_organizations(
    service: AuthServiceDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """获取当前用户可用的部门列表"""
    return await service.list_my_orgs(current_user.id)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    service: AuthServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    roles: list[str] = Depends(get_current_roles),
) -> Any:
    """获取当前登录用户信息"""
    return await service.get_me(user=current_user, org_id=org_id, tenant_id=tenant_id)


@router.get("/menu-tree")
async def get_menu_tree(
    service: AuthServiceDep,
    org_user: OrganizationUser = Depends(get_current_org_user),
    tenant_id: int = Depends(get_current_tenant_id),
) -> Any:
    """获取当前用户的动态导航菜单"""
    return await service.get_menu_tree(org_user=org_user, tenant_id=tenant_id)


@router.put("/update-password", response_model=dict)
async def update_password(
    data: UserUpdatePassword,
    service: AuthServiceDep,
    current_user: User = Depends(get_current_user),
):
    """修改密码"""
    return await service.update_password(
        user=current_user, current_password=data.current_password, new_password=data.new_password
    )


@router.put("/me/profile")
async def update_my_profile(
    data: UserProfileUpdate,
    service: AuthServiceDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """修改用户基本信息"""
    return await service.update_profile(user=current_user, data=data.model_dump(exclude_unset=True))


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, service: AuthServiceDep):
    """请求密码重置"""
    return await service.forgot_password(data.email)


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, service: AuthServiceDep):
    """使用验证码重置密码"""
    return await service.reset_password(email=data.email, code=data.code, new_password=data.new_password)
