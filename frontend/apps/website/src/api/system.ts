import { apiClient } from "./client";

// ═══════════════════════════════════════
//  租户管理
// ═══════════════════════════════════════

export interface TenantItem {
  id: string;
  name: string;
  slug: string;
  status: string;
  plan_type: string;
  quota_tokens_limit: number;
  quota_tokens_used: number;
  max_members: number | null;
  max_patients: number | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  org_type: string | null;
  address: string | null;
  org_count: number;
  created_at: string;
}

export interface TenantCreateReq {
  name: string;
  slug: string;
  plan_type?: string;
  status?: string;
  quota_tokens_limit?: number;
  max_members?: number | null;
  max_patients?: number | null;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  org_type?: string;
  address?: string;
}

export async function listTenants(params?: {
  search?: string;
  status?: string;
  skip?: number;
  limit?: number;
}): Promise<TenantItem[]> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.status) sp.set("status", params.status);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiClient.get(`tenants${qs ? `?${qs}` : ""}`).json<TenantItem[]>();
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
  tenant_id: string;
  description: string | null;
  sort: number;
  created_at: string;
}

export interface OrgCreateReq {
  name: string;
  code: string;
  tenant_id?: string;
  status?: string;
  description?: string;
}

export async function listOrgs(params?: {
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<OrgItem[]> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiClient.get(`organizations${qs ? `?${qs}` : ""}`).json<OrgItem[]>();
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
  user_id: string;
  email: string;
  name: string | null;
  roles: string[];
  user_type: string;
}

export async function listOrgMembers(orgId: string): Promise<OrgMemberItem[]> {
  return apiClient.get(`organizations/${orgId}/members`).json<OrgMemberItem[]>();
}

export async function removeOrgMember(orgId: string, userId: string): Promise<void> {
  await apiClient.delete(`organizations/${orgId}/members/${userId}`);
}

// ═══════════════════════════════════════
//  用户管理
// ═══════════════════════════════════════

export interface UserItem {
  id: string;
  email: string;
  name: string | null;
  created_at: string;
  org_count: number;
}

export interface UserCreateReq {
  email: string;
  name?: string;
  password: string;
}

export async function listUsers(params?: {
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<UserItem[]> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiClient.get(`users${qs ? `?${qs}` : ""}`).json<UserItem[]>();
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
  await apiClient.put(`users/${id}/status`, { searchParams: { is_active: String(isActive) } });
}

// ═══════════════════════════════════════
//  角色管理（复用 rbac 端点）
// ═══════════════════════════════════════

export interface RoleItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  parent_role_id: string | null;
  permissions: { id: string; code: string; name: string }[];
}

export interface RoleCreateReq {
  name: string;
  code: string;
  description?: string;
  parent_role_id?: string;
  permission_ids: string[];
}

export async function listRoles(): Promise<RoleItem[]> {
  return apiClient.get("rbac/roles").json<RoleItem[]>();
}

export async function createRole(data: RoleCreateReq): Promise<RoleItem> {
  return apiClient.post("rbac/roles", { json: data }).json<RoleItem>();
}

export async function updateRole(
  id: string,
  data: { name?: string; description?: string; permission_ids?: string[] },
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
  parent_id: string | null;
  name: string;
  code: string;
  menu_type: string;
  path: string | null;
  icon: string | null;
  permission_code: string | null;
  sort: number;
  is_visible: boolean;
  is_enabled: boolean;
  children: MenuItemData[];
}

export interface MenuCreateReq {
  parent_id?: string;
  name: string;
  code: string;
  menu_type?: string;
  path?: string;
  icon?: string;
  permission_code?: string;
  sort?: number;
  is_visible?: boolean;
  is_enabled?: boolean;
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
