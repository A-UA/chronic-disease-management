export default function access(initialState: { currentUser?: any } | undefined) {
  const { currentUser } = initialState || {};
  const permissions = currentUser?.permissions || [];

  return {
    // 1. Generic check function
    can: (code: string) => permissions.includes(code),

    // 2. Predefined semantic access rules
    canViewPatients: permissions.includes('patient:read'),
    canUpdatePatient: permissions.includes('patient:update'),
    
    canManageKB: permissions.includes('kb:manage'),
    canManageDocs: permissions.includes('doc:manage'),
    
    canUseChat: permissions.includes('chat:use'),
    
    canManageOrg: permissions.includes('org_member:manage'),
    canViewUsage: permissions.includes('org_usage:read'),

    // 3. Platform level
    isPlatformAdmin: permissions.includes('platform_settings:manage'),
    isPlatformViewer: permissions.includes('audit_log:read'),
  };
}
