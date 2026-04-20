export const AUTH_SERVICE = 'AUTH_SERVICE';
export const PATIENT_SERVICE = 'PATIENT_SERVICE';
export const AI_SERVICE = 'AI_SERVICE';

export const AUTH_TCP_PORT = 8011;
export const PATIENT_TCP_PORT = 8021;
export const AI_TCP_PORT = 8031;

// 知识库命令（由 ai-service 处理）
export const KNOWLEDGE_BASE_FIND_ALL = 'kb_find_all';
export const KNOWLEDGE_BASE_CREATE = 'kb_create';
export const KNOWLEDGE_BASE_STATS = 'kb_stats';
export const KNOWLEDGE_BASE_DELETE = 'kb_delete';

export const DOCUMENT_FIND_BY_KB = 'document_find_by_kb';
export const DOCUMENT_CREATE_SYNC = 'document_create_sync';
export const DOCUMENT_DELETE = 'document_delete';
export const DOCUMENT_FIND_ONE = 'document_find_one';

// 会话命令
export const CONVERSATION_FIND_ALL = 'conv_find_all';
export const CONVERSATION_FIND_ONE = 'conv_find_one';
export const CONVERSATION_CREATE = 'conv_create';
export const CONVERSATION_DELETE = 'conv_delete';
export const MESSAGE_CREATE = 'msg_create';

// 知识库归属校验
export const KB_VERIFY_OWNERSHIP = 'kb_verify_ownership';

// Dashboard 统计命令
export const AUTH_DASHBOARD_STATS = 'auth_dashboard_stats';
export const PATIENT_DASHBOARD_STATS = 'patient_dashboard_stats';
export const AI_DASHBOARD_STATS = 'ai_dashboard_stats';
