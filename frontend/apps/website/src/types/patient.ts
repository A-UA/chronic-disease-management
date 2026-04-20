export interface PatientProfile {
  id: string;
  userId: string;
  orgId: string;
  real_name: string | null;
  gender: string | null;
  birth_date: string | null;
  medical_history: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface HealthMetric {
  id: string;
  patient_id: string;
  metric_type: string;
  value: number;
  value_secondary: number | null;
  unit: string;
  measuredAt: string;
  note: string | null;
  createdAt: string;
}

export interface ManagementSuggestion {
  id: string;
  patient_id: string;
  manager_id: string;
  suggestion_type: string;
  content: string;
  createdAt: string;
}
