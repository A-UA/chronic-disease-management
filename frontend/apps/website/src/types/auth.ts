export interface LoginRequest {
  username: string;
  password: string;
}

/** 单部门登录直接返回的完整响应 */
export interface LoginSuccessResponse {
  accessToken: string;
  tokenType: string;
  requireOrgSelection: false;
  organization: OrgBrief;
}

/** 多部门登录需要选择部门的响应 */
export interface OrgSelectionResponse {
  accessToken: null;
  tokenType: string;
  requireOrgSelection: true;
  selectionToken: string;
  organizations: OrgBrief[];
}

/** 登录接口的联合类型响应 */
export type LoginResponse = LoginSuccessResponse | OrgSelectionResponse;

/** 部门摘要信息 */
export interface OrgBrief {
  id: string;
  name: string;
  tenantId: string;
  tenant_name?: string | null;
}

/** select-org / switch-org 返回 */
export interface SelectOrgResponse {
  accessToken: string;
  tokenType: string;
  organization: OrgBrief;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string | null;
  orgId: string | null;
  permissions: string[];
}

export interface MenuItem {
  id: string;
  name: string;
  code: string;
  menuType: "directory" | "page" | "link";
  path: string | null;
  icon: string | null;
  permissionCode: string | null;
  sort: number;
  isVisible: boolean;
  isEnabled: boolean;
  meta: Record<string, unknown> | null;
  children: MenuItem[];
}
