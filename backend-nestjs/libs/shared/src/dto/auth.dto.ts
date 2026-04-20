import type { IdentityPayload } from '../interfaces/identity.interface.js';

// ─── Auth 微服务 TCP 消息载荷 ───

export interface LoginPayload {
  username: string;
  password: string;
}

export interface SelectOrgPayload {
  orgId: string;
  selectionToken: string;
}

export interface SwitchOrgPayload {
  identity: IdentityPayload;
  orgId: string;
}

export interface IdentityOnlyPayload {
  identity: IdentityPayload;
}

// ─── Auth 域的创建 / 更新数据体 ───

export interface CreateUserData {
  email: string;
  password?: string;
  name?: string;
  orgId?: string;
  roleIds?: string[];
}

export interface UpdateUserData {
  email?: string;
  password?: string;
  name?: string;
}

export interface CreateTenantData {
  name: string;
  slug: string;
  planType?: string;
}

export interface UpdateTenantData {
  name?: string;
  slug?: string;
  planType?: string;
}

export interface CreateOrgData {
  name: string;
  code: string;
  tenantId: string;
  parentId?: string | null;
  status?: string;
}

export interface UpdateOrgData {
  name?: string;
  code?: string;
  parentId?: string | null;
  status?: string;
}

export interface CreateRoleData {
  name: string;
  code: string;
  tenantId?: string | null;
  parentRoleId?: string | null;
  isSystem?: boolean;
}

export interface UpdateRoleData {
  name?: string;
  code?: string;
  parentRoleId?: string | null;
}

export interface CreatePermissionData {
  name: string;
  code: string;
  resourceId: string;
  actionId: string;
}

export interface UpdatePermissionData {
  name?: string;
  code?: string;
  resourceId?: string;
  actionId?: string;
}

export interface CreateMenuData {
  name: string;
  code: string;
  menuType?: string;
  path?: string | null;
  icon?: string | null;
  parentId?: string | null;
  tenantId?: string | null;
  permissionCode?: string | null;
  sort?: number;
  isVisible?: boolean;
  isEnabled?: boolean;
  meta?: Record<string, unknown> | null;
}

export interface UpdateMenuData {
  name?: string;
  code?: string;
  menuType?: string;
  path?: string | null;
  icon?: string | null;
  parentId?: string | null;
  permissionCode?: string | null;
  sort?: number;
  isVisible?: boolean;
  isEnabled?: boolean;
  meta?: Record<string, unknown> | null;
}
