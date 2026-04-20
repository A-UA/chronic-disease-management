import { apiClient } from "./client";

export interface DashboardStats {
  totalOrganizations: number;
  totalUsers: number;
  totalPatients: number;
  totalConversations: number;
  activeUsers24h: number;
  totalTokensUsed: number;
  recentFailedDocs: number;
  tokenUsageTrend: { date: string; tokens: number }[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient.get("dashboard/stats").json<DashboardStats>();
}
