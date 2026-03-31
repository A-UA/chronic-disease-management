/**
 * @see https://umijs.org/docs/max/access
 * */
export default function access(initialState: { permissions?: string[] } | undefined) {
  const { permissions = [] } = initialState || {};

  return {
    // 租户基础权限
    canViewDashboard: permissions.includes('menu:dashboard'),
    canViewPatients: permissions.includes('menu:patients'),
    canViewKB: permissions.includes('menu:knowledge'),
    canViewChat: permissions.includes('menu:chat'),
    canViewMembers: permissions.includes('menu:members'),
    canViewRoles: permissions.includes('menu:roles'),
    canViewAudit: permissions.includes('menu:settings'),

    // 数据操作权限
    canUpdatePatient: permissions.includes('patient:update'),
    canManageKB: permissions.includes('kb:manage'),
    canManageMembers: permissions.includes('org_member:manage'),
  };
}
