import { apiClient } from "./client";

// ── 成员管理 ──

export interface OrgMember {
  id: string;
  userId: string;
  email: string;
  name: string | null;
  userType: "staff" | "patient";
  roles: { id: string; code: string; name: string }[];
  createdAt: string;
}

export interface InviteRequest {
  email: string;
  roleId: string;
}

export async function listMembers(): Promise<OrgMember[]> {
  return apiClient.get("organizations/members").json<OrgMember[]>();
}

export async function inviteMember(data: InviteRequest): Promise<{ id: string }> {
  return apiClient.post("organizations/invite", { json: data }).json();
}

export async function removeMember(userId: string): Promise<void> {
  await apiClient.delete(`organizations/members/${userId}`);
}

// ── 角色 ──

export interface RoleItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  isSystem: boolean;
  permissions: { id: string; code: string; name: string }[];
}

export async function listRoles(): Promise<RoleItem[]> {
  return apiClient.get("rbac/roles").json<RoleItem[]>();
}

export async function createRole(data: {
  name: string;
  description?: string;
  permissionIds: string[];
}): Promise<RoleItem> {
  return apiClient.post("rbac/roles", { json: data }).json<RoleItem>();
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
