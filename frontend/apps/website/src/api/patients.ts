import { apiClient } from "./client";
import type { PatientProfile } from "@/types/patient";

export async function getPatients(params?: {
  skip?: number;
  limit?: number;
  search?: string;
}): Promise<PatientProfile[]> {
  return apiClient.get("patients", { searchParams: params ?? {} }).json<PatientProfile[]>();
}

export async function getPatientById(id: string): Promise<PatientProfile> {
  return apiClient.get(`patients/${id}`).json<PatientProfile>();
}

export async function deletePatient(id: string): Promise<void> {
  await apiClient.delete(`patients/${id}`);
}
