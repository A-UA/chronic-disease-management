import { apiClient } from "./client";
import type { LoginResponse, SelectOrgResponse, UserInfo, MenuItem, OrgBrief } from "@/types/auth";

export async function loginApi(username: string, password: string): Promise<LoginResponse> {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  return apiClient
    .post("auth/login/access-token", {
      body: formData,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
    .json<LoginResponse>();
}

/** 多部门登录时，用 selectionToken 选择部门 */
export async function selectOrgApi(
  orgId: string,
  selectionToken: string,
): Promise<SelectOrgResponse> {
  return apiClient
    .post("auth/select-org", {
      json: { orgId: orgId, selectionToken: selectionToken },
    })
    .json<SelectOrgResponse>();
}

/** 已登录用户切换部门 */
export async function switchOrgApi(orgId: string): Promise<SelectOrgResponse> {
  return apiClient.post("auth/switch-org", { json: { orgId: orgId } }).json<SelectOrgResponse>();
}

/** 获取当前用户可用的部门列表 */
export async function getMyOrgsApi(): Promise<OrgBrief[]> {
  return apiClient.get("auth/my-orgs").json<OrgBrief[]>();
}

export async function getMeApi(): Promise<UserInfo> {
  return apiClient.get("auth/me").json<UserInfo>();
}

export async function getMenuTreeApi(): Promise<MenuItem[]> {
  return apiClient.get("auth/menu-tree").json<MenuItem[]>();
}
