export default (initialState: any) => {
  const { currentUser } = initialState || {};
  const platformRoles: string[] = currentUser?.platformRoles || [];
  const orgRoles: string[] = currentUser?.orgRoles || [];

  return {
    // canPlatformAdmin: platformRoles.includes('platform_admin'),
    // canPlatformView: platformRoles.some((r: string) =>
    //   ['platform_admin', 'platform_viewer'].includes(r),
    // ),
    // canOrgAdmin: orgRoles.some((r: string) =>
    //   ['owner', 'admin'].includes(r),
    // ),
    // canManageMembers: orgRoles.some((r: string) =>
    //   ['owner', 'admin'].includes(r),
    // ),
    // canManagePatients: orgRoles.some((r: string) =>
    //   ['owner', 'admin', 'manager'].includes(r),
    // ),
    // canManageKB: orgRoles.some((r: string) =>
    //   ['owner', 'admin', 'manager'].includes(r),
    // ),
  };
};
