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

// ─── 知识库 TCP 消息载荷 ───

export interface CreateKbPayload {
  identity: IdentityPayload;
  data: CreateKbData;
}

export interface CreateKbData {
  name: string;
  description?: string;
}

export interface KbIdPayload {
  identity: IdentityPayload;
  id: string;
}

export interface DocsByKbPayload {
  kbId: string;
}

export interface SyncDocumentPayload {
  identity: IdentityPayload;
  kbId: string;
  fileName: string;
  fileType?: string;
  fileSize?: number;
  minioUrl: string;
  chunkCount?: number;
  status?: string;
}

export interface DeleteDocPayload {
  id: string;
}
