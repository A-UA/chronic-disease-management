// ─── Auth 域出站视图对象 ───

/** 用户视图（脱敏，排除 passwordHash） */
export interface UserVO {
  id: string;
  email: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
}

/** 租户视图 */
export interface TenantVO {
  id: string;
  name: string;
  slug: string;
  planType: string;
  createdAt: Date;
}

/** 组织视图 */
export interface OrganizationVO {
  id: string;
  tenantId: string;
  parentId: string | null;
  name: string;
  code: string;
  status: string;
  createdAt: Date;
  updatedAt: Date;
}

/** 组织摘要（登录/选择组织场景使用的轻量视图） */
export interface OrganizationSummaryVO {
  id: string;
  name: string;
  tenant_id: string;
}

/** 角色视图 */
export interface RoleVO {
  id: string;
  tenantId: string | null;
  parentRoleId: string | null;
  name: string;
  code: string;
  isSystem: boolean;
  createdAt: Date;
  updatedAt: Date;
}

/** 权限视图 */
export interface PermissionVO {
  id: string;
  name: string;
  code: string;
  resourceId: string;
  actionId: string;
}

/** 菜单视图 */
export interface MenuVO {
  id: string;
  parentId: string | null;
  tenantId: string | null;
  name: string;
  code: string;
  menuType: string;
  path: string | null;
  icon: string | null;
  permissionCode: string | null;
  sort: number;
  isVisible: boolean;
  isEnabled: boolean;
  meta: Record<string, unknown> | null;
  createdAt: Date;
  updatedAt: Date;
}

// ─── 复合响应 VO ───

/** 登录响应（单组织直接签发 token） */
export interface LoginResultVO {
  access_token: string | null;
  token_type: 'bearer';
  organization?: OrganizationSummaryVO;
  organizations?: OrganizationSummaryVO[];
  require_org_selection: boolean;
  selection_token?: string;
}

/** 选择/切换组织响应 */
export interface OrgTokenResultVO {
  access_token: string;
  token_type: 'bearer';
  organization: OrganizationSummaryVO;
}

/** 当前用户信息 */
export interface CurrentUserVO {
  id: string;
  email: string;
  name: string;
  created_at: Date;
  tenant_id: string;
  org_id: string;
  permissions: string[];
}

/** 操作成功响应 */
export interface SuccessVO {
  success: true;
}
