import { apiClient } from "./client";

// ── 通用分页响应 ──
export interface PaginatedResult<T> {
  total: number;
  items: T[];
}

// ═══════════════════════════════════════
//  租户管理
// ═══════════════════════════════════════

export interface TenantItem {
  id: string;
  name: string;
  slug: string;
  status: string;
  planType: string;
  quotaTokensLimit: number;
  quotaTokensUsed: number;
  maxMembers: number | null;
  maxPatients: number | null;
  contactName: string | null;
  contactPhone: string | null;
  contactEmail: string | null;
  orgType: string | null;
  address: string | null;
  orgCount: number;
  createdAt: string;
}

export interface TenantCreateReq {
  name: string;
  slug: string;
  planType?: string;
  status?: string;
  quotaTokensLimit?: number;
  maxMembers?: number | null;
  maxPatients?: number | null;
  contactName?: string;
  contactPhone?: string;
  contactEmail?: string;
  orgType?: string;
  address?: string;
}

export async function listTenants(params?: {
  search?: string;
  status?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResult<TenantItem>> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.status) sp.set("status", params.status);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiClient.get(`tenants${qs ? `?${qs}` : ""}`).json<PaginatedResult<TenantItem>>();
}

export async function createTenant(data: TenantCreateReq): Promise<TenantItem> {
  return apiClient.post("tenants", { json: data }).json<TenantItem>();
}

export async function updateTenant(
  id: string,
  data: Partial<TenantCreateReq>,
): Promise<TenantItem> {
  return apiClient.put(`tenants/${id}`, { json: data }).json<TenantItem>();
}

export async function deleteTenant(id: string): Promise<void> {
  await apiClient.delete(`tenants/${id}`);
}

// ═══════════════════════════════════════
//  组织管理
// ═══════════════════════════════════════

export interface OrgItem {
  id: string;
  name: string;
  code: string;
  status: string;
  tenantId: string;
  description: string | null;
  sort: number;
  createdAt: string;
}

export interface OrgCreateReq {
  name: string;
  code: string;
  tenantId?: string;
  status?: string;
  description?: string;
  parentId?: string;
}

export async function listOrgs(params?: {
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResult<OrgItem>> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiClient.get(`organizations${qs ? `?${qs}` : ""}`).json<PaginatedResult<OrgItem>>();
}

export async function createOrg(data: OrgCreateReq): Promise<OrgItem> {
  return apiClient.post("organizations", { json: data }).json<OrgItem>();
}

export async function updateOrg(id: string, data: Partial<OrgCreateReq>): Promise<OrgItem> {
  return apiClient.put(`organizations/${id}`, { json: data }).json<OrgItem>();
}

export async function deleteOrg(id: string): Promise<void> {
  await apiClient.delete(`organizations/${id}`);
}

// 组织成员（复用 members API 的类型）
export interface OrgMemberItem {
  userId: string;
  email: string;
  name: string | null;
  roles: string[];
  userType: string;
}

export async function listOrgMembers(orgId: string): Promise<OrgMemberItem[]> {
  return apiClient.get(`organizations/${orgId}/members`).json<OrgMemberItem[]>();
}

export async function removeOrgMember(orgId: string, userId: string): Promise<void> {
  await apiClient.delete(`organizations/${orgId}/members/${userId}`);
}

export async function addOrgMember(
  orgId: string,
  data: { userId: string; roleIds?: string[]; userType?: string },
): Promise<void> {
  await apiClient.post(`organizations/${orgId}/members`, { json: data });
}

// ═══════════════════════════════════════
//  用户管理
// ═══════════════════════════════════════

export interface UserItem {
  id: string;
  email: string;
  name: string | null;
  createdAt: string;
  orgCount: number;
}

export interface UserCreateReq {
  email: string;
  name?: string;
  password: string;
  orgId?: string;
  roleIds?: string[];
}

export async function listUsers(params?: {
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResult<UserItem>> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiClient.get(`users${qs ? `?${qs}` : ""}`).json<PaginatedResult<UserItem>>();
}

export async function createUser(data: UserCreateReq): Promise<UserItem> {
  return apiClient.post("users", { json: data }).json<UserItem>();
}

export async function updateUser(
  id: string,
  data: { name?: string; email?: string },
): Promise<UserItem> {
  return apiClient.put(`users/${id}`, { json: data }).json<UserItem>();
}

export async function deleteUser(id: string): Promise<void> {
  await apiClient.delete(`users/${id}`);
}

export async function setUserStatus(id: string, isActive: boolean): Promise<void> {
  await apiClient.put(`users/${id}/status`, { searchParams: { isActive: String(isActive) } });
}

// ═══════════════════════════════════════
//  角色管理（复用 rbac 端点）
// ═══════════════════════════════════════

export interface RoleItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  isSystem: boolean;
  parentRoleId: string | null;
  permissions: { id: string; code: string; name: string }[];
  userCount?: number;
}

export interface RoleCreateReq {
  name: string;
  code: string;
  description?: string;
  parentRoleId?: string;
  permissionIds: string[];
}

export async function listRoles(): Promise<RoleItem[]> {
  return apiClient.get("rbac/roles").json<RoleItem[]>();
}

export async function createRole(data: RoleCreateReq): Promise<RoleItem> {
  return apiClient.post("rbac/roles", { json: data }).json<RoleItem>();
}

export async function updateRole(
  id: string,
  data: { name?: string; description?: string; permissionIds?: string[] },
): Promise<RoleItem> {
  return apiClient.put(`rbac/roles/${id}`, { json: data }).json<RoleItem>();
}

export async function deleteRole(id: string): Promise<void> {
  await apiClient.delete(`rbac/roles/${id}`);
}

export interface PermissionItem {
  id: string;
  code: string;
  name: string;
}

export async function listPermissions(): Promise<PermissionItem[]> {
  return apiClient.get("rbac/permissions").json<PermissionItem[]>();
}

// ═══════════════════════════════════════
//  菜单管理
// ═══════════════════════════════════════

export interface MenuItemData {
  id: string;
  parentId: string | null;
  name: string;
  code: string;
  menuType: string;
  path: string | null;
  icon: string | null;
  permissionCode: string | null;
  sort: number;
  isVisible: boolean;
  isEnabled: boolean;
  children: MenuItemData[];
}

export interface MenuCreateReq {
  parentId?: string;
  name: string;
  code: string;
  menuType?: string;
  path?: string;
  icon?: string;
  permissionCode?: string;
  sort?: number;
  isVisible?: boolean;
  isEnabled?: boolean;
}

export async function listMenus(): Promise<MenuItemData[]> {
  return apiClient.get("menus").json<MenuItemData[]>();
}

export async function createMenu(data: MenuCreateReq): Promise<MenuItemData> {
  return apiClient.post("menus", { json: data }).json<MenuItemData>();
}

export async function updateMenu(id: string, data: Partial<MenuCreateReq>): Promise<MenuItemData> {
  return apiClient.put(`menus/${id}`, { json: data }).json<MenuItemData>();
}

export async function deleteMenu(id: string): Promise<void> {
  await apiClient.delete(`menus/${id}`);
}
