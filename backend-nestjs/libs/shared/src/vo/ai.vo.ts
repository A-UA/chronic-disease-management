// ─── AI 域出站视图对象 ───

/** 会话视图 */
export interface ConversationVO {
  id: string;
  tenantId: string;
  orgId: string;
  userId: string;
  kbId: string | null;
  title: string;
  messageCount: number;
  totalTokens: number;
  lastMessageAt: Date;
  createdAt: Date;
}

/** 会话详情视图（含消息列表） */
export interface ConversationDetailVO extends ConversationVO {
  messages: ChatMessageVO[];
}

/** 聊天消息视图 */
export interface ChatMessageVO {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: CitationVO[] | null;
  metadata: Record<string, unknown> | null;
  tokenCount: number;
  createdAt: Date;
}

import type { Citation } from '../interfaces/citation.interface.js';

/** 引用视图（类型别名，指向统一 Citation） */
export type CitationVO = Citation;

/** KB 归属校验结果 */
export interface KbOwnershipResultVO {
  valid: boolean;
  kbId: string;
  tenantId: string;
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

/** Token 使用趋势条目 */
export interface TokenUsageTrendItem {
  date: string;
  tokens: number;
}

/** AI 域仪表盘统计 */
export interface AiDashboardStatsVO {
  totalConversations: number;
  totalTokensUsed: number;
  recentFailedDocs: number;
  tokenUsageTrend: TokenUsageTrendItem[];
}

/** Gateway 聚合的完整仪表盘统计 */
export interface DashboardStatsVO {
  totalOrganizations: number;
  totalUsers: number;
  totalPatients: number;
  totalConversations: number;
  activeUsers24h: number;
  totalTokensUsed: number;
  recentFailedDocs: number;
  tokenUsageTrend: TokenUsageTrendItem[];
}
