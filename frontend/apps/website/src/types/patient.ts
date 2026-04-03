export interface PatientProfile {
  id: string;
  user_id: string;
  org_id: string;
  real_name: string | null;
  gender: string | null;
  birth_date: string | null;
  medical_history: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface HealthMetric {
  id: string;
  patient_id: string;
  metric_type: string;
  value: number;
  value_secondary: number | null;
  unit: string;
  measured_at: string;
  note: string | null;
  created_at: string;
}

export interface ManagementSuggestion {
  id: string;
  patient_id: string;
  manager_id: string;
  suggestion_type: string;
  content: string;
  created_at: string;
}
