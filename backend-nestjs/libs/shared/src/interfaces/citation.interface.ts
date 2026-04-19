/**
 * 引用数据结构 — DTO/VO/Entity 的统一类型
 *
 * JSONB 存储 ↔ Agent 传入 ↔ 前端响应 全链路复用
 */
export interface Citation {
  ref: string;
  source: string;
  snippet: string;
  page?: number;
}
