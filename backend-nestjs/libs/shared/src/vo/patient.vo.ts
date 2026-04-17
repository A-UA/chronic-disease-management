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

/** 知识库视图 */
export interface KnowledgeBaseVO {
  id: string;
  tenantId: string;
  orgId: string;
  createdBy: string;
  name: string;
  description: string;
}

/** 知识库统计 */
export interface KnowledgeBaseStatsVO {
  document_count: number;
  chunk_count: number;
  total_tokens: number;
}

/** 文档视图 */
export interface DocumentVO {
  id: string;
  kbId: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  minioUrl: string;
}

/** 文档同步结果 */
export interface DocumentSyncResultVO {
  id: string;
  kbId: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  minioUrl: string;
  chunkCount?: number;
  status?: string;
}
