export interface PatientProfile {
  id: string;
  userId: string;
  orgId: string;
  name: string;
  gender: string | null;
  birthDate: string | null;
  medicalHistory: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface HealthMetric {
  id: string;
  patientId: string;
  metricType: string;
  value: number;
  valueSecondary: number | null;
  unit: string;
  measuredAt: string;
  note: string | null;
  createdAt: string;
}

export interface ManagementSuggestion {
  id: string;
  patientId: string;
  managerId: string;
  suggestionType: string;
  content: string;
  createdAt: string;
}
