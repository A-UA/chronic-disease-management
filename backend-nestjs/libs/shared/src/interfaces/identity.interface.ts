export interface IdentityPayload {
  userId: string;
  tenantId: string;
  orgId: string;
  allowedOrgIds: string[];
  roles: string[];
}
