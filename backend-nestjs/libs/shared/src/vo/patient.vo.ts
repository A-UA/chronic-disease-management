// ─── Patient 域出站视图对象 ───

/** 患者视图 */
export interface PatientVO {
  id: string;
  tenantId: string;
  orgId: string;
  name: string;
  gender: string;
}

/** 健康指标视图 */
export interface HealthMetricVO {
  id: string;
  patientId: string;
  metricType: string;
  metricValue: string;
  recordedAt: Date;
}

/** 管理建议视图 */
export interface ManagementSuggestionVO {
  id: string;
  patientId: string;
  createdByUserId: string;
  suggestionType: string;
  content: string;
  status: string;
  createdAt: Date;
}

/** 管理人分配视图 */
export interface ManagerAssignmentVO {
  id: string;
  patientId: string;
  managerUserId: string;
  assignmentType: string;
  createdAt: Date;
}

/** 家属关联视图 */
export interface PatientFamilyLinkVO {
  id: string;
  patientId: string;
  familyUserId: string;
  relationship: string;
  createdAt: Date;
}

/** Patient 域仪表盘统计 */
export interface PatientDashboardStatsVO {
  totalPatients: number;
}

