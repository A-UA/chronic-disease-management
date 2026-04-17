/** 引用来源 */
export interface Citation {
  source: string;
  content: string;
}

/** 聊天消息 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  citations?: Citation[];
}

/** 聊天会话 */
export interface ChatConversation {
  id: string;
  kb_id: string;
  title: string | null;
  created_at: string;
  messages: ChatMessage[];
  user_id: string;
}

/** Agent 解析文档响应 */
export interface ParseDocumentResponse {
  chunk_count: number;
}
