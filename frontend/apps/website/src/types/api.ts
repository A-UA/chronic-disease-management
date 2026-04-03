export interface ApiError {
  detail: string;
}

export interface PaginatedParams {
  skip?: number;
  limit?: number;
  search?: string;
}
