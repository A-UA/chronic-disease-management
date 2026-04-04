export interface LoginRequest {
  username: string;
  password: string;
}

/** 单部门登录直接返回的完整响应 */
export interface LoginSuccessResponse {
  access_token: string;
  token_type: string;
  require_org_selection: false;
  organization: OrgBrief;
}

/** 多部门登录需要选择部门的响应 */
export interface OrgSelectionResponse {
  access_token: null;
  token_type: string;
  require_org_selection: true;
  selection_token: string;
  organizations: OrgBrief[];
}

/** 登录接口的联合类型响应 */
export type LoginResponse = LoginSuccessResponse | OrgSelectionResponse;

/** 部门摘要信息 */
export interface OrgBrief {
  id: string;
  name: string;
  tenant_id: string;
  tenant_name?: string | null;
}

/** select-org / switch-org 返回 */
export interface SelectOrgResponse {
  access_token: string;
  token_type: string;
  organization: OrgBrief;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string | null;
  org_id: string | null;
  permissions: string[];
}

export interface MenuItem {
  id: string;
  name: string;
  code: string;
  menu_type: "directory" | "page" | "link";
  path: string | null;
  icon: string | null;
  permission_code: string | null;
  sort: number;
  is_visible: boolean;
  is_enabled: boolean;
  meta: Record<string, unknown> | null;
  children: MenuItem[];
}
