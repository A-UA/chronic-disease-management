import { apiClient } from "./client";
import type { HealthMetric } from "@/types/patient";

export async function getPatientTrend(
  patientId: string,
  metricType: string,
  days: number = 30,
): Promise<HealthMetric[]> {
  return apiClient
    .get(`health-metrics/patients/${patientId}/trend`, {
      searchParams: { metricType, days },
    })
    .json<HealthMetric[]>();
}
