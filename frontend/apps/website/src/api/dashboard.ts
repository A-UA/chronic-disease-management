import { apiClient } from "./client";

export interface DashboardStats {
  total_organizations: number;
  total_users: number;
  total_patients: number;
  total_conversations: number;
  active_users_24h: number;
  total_tokens_used: number;
  recent_failed_docs: number;
  token_usage_trend: { date: string; tokens: number }[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient.get("dashboard/stats").json<DashboardStats>();
}
