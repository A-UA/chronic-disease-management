import type { IdentityPayload } from '../interfaces/identity.interface.js';

// ─── Patient 微服务 TCP 消息载荷 ───

/** 按患者查询（带租户隔离） */
export interface PatientIdPayload {
  identity: IdentityPayload;
  patientId: string;
}

/** 创建患者 */
export interface CreatePatientPayload {
  identity: IdentityPayload;
  name: string;
  gender: string;
}

/** 创建健康指标 */
export interface CreateHealthMetricPayload {
  identity: IdentityPayload;
  patientId: string;
  metricType: string;
  metricValue: string;
}

/** 创建管理建议 */
export interface CreateSuggestionPayload {
  identity: IdentityPayload;
  patientId: string;
  suggestionType: string;
  content: string;
}

/** 分配管理人 */
export interface AssignManagerPayload {
  identity: IdentityPayload;
  patientId: string;
  managerUserId: string;
  assignmentType: string;
}

/** 关联家属 */
export interface LinkFamilyPayload {
  identity: IdentityPayload;
  patientId: string;
  familyUserId: string;
  relationship: string;
}

