import type { IdentityPayload } from '../interfaces/identity.interface.js';
import type { PaginationQuery } from './pagination.dto.js';

// ─── 通用 CRUD 微服务消息载荷 ───

/** 列表查询载荷（TCP 消息） */
export interface ListPayload extends PaginationQuery {
  identity: IdentityPayload;
}

/** 创建载荷（TCP 消息） */
export interface CreatePayload<T> {
  identity: IdentityPayload;
  data: T;
}

/** 更新载荷（TCP 消息） */
export interface UpdatePayload<T> {
  identity: IdentityPayload;
  id: string;
  data: T;
}

/** 删除载荷（TCP 消息） */
export interface DeletePayload {
  identity: IdentityPayload;
  id: string;
}
