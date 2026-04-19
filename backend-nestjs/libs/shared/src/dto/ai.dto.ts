import type { IdentityPayload } from '../interfaces/identity.interface.js';

// ─── AI 微服务 TCP 消息载荷 ───

/** 创建会话 */
export interface CreateConversationPayload {
  identity: IdentityPayload;
  kbId?: string;
  title?: string;
}

/** 查询会话 */
export interface ConversationIdPayload {
  identity: IdentityPayload;
  id: string;
}

/** 创建消息 */
export interface CreateMessagePayload {
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: CitationData[];
  metadata?: Record<string, unknown>;
  tokenCount?: number;
}

import type { Citation } from '../interfaces/citation.interface.js';

/** 引用数据（类型别名，指向统一 Citation） */
export type CitationData = Citation;

/** KB 归属校验 */
export interface KbVerifyOwnershipPayload {
  kbId: string;
  tenantId: string;
}

// ─── 知识库 TCP 消息载荷（从 patient.dto.ts 迁入） ───

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

// ─── Gateway 入站 DTO ───

/** 聊天请求体 */
export interface ChatRequestDto {
  kb_id: string;
  query: string;
  conversation_id?: string;
}

/** SSE 流结束载荷 */
export interface StreamDonePayload {
  done: true;
  citations?: CitationData[];
}
