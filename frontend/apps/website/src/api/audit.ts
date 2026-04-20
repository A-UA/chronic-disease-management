import { apiClient } from "./client";

export interface AuditLogItem {
  id: string;
  userId: string;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  details: string | null;
  createdAt: string;
}

export interface AuditLogQuery {
  action?: string;
  resource_type?: string;
  skip?: number;
  limit?: number;
}

export async function listAuditLogs(params: AuditLogQuery = {}): Promise<AuditLogItem[]> {
  const searchParams = new URLSearchParams();
  if (params.action) searchParams.set("action", params.action);
  if (params.resource_type) searchParams.set("resource_type", params.resource_type);
  if (params.skip != null) searchParams.set("skip", String(params.skip));
  if (params.limit != null) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return apiClient.get(`audit-logs${qs ? `?${qs}` : ""}`).json<AuditLogItem[]>();
}
