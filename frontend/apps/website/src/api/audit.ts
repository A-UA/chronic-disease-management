import { apiClient } from "./client";

export interface AuditLogItem {
  id: string;
  userId: string;
  userEmail?: string;
  action: string;
  resourceType: string;
  resourceId: string | null;
  ipAddress: string | null;
  details: string | null;
  createdAt: string;
}

export interface AuditLogQuery {
  action?: string;
  resourceType?: string;
  skip?: number;
  limit?: number;
}

export async function listAuditLogs(params: AuditLogQuery = {}): Promise<AuditLogItem[]> {
  const searchParams = new URLSearchParams();
  if (params.action) searchParams.set("action", params.action);
  if (params.resourceType) searchParams.set("resourceType", params.resourceType);
  if (params.skip != null) searchParams.set("skip", String(params.skip));
  if (params.limit != null) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return apiClient.get(`audit-logs${qs ? `?${qs}` : ""}`).json<AuditLogItem[]>();
}
