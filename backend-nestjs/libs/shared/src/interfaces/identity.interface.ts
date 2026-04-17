export interface IdentityPayload {
  userId: number;
  tenantId: number;
  orgId: number;
  allowedOrgIds: number[];
  roles: string[];
}
