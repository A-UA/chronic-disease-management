/** 分页查询参数 */
export interface PaginationQuery {
  skip?: number;
  limit?: number;
}

/** 分页结果 */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
}
