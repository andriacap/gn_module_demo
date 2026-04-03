export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  limit: number;
  pages: number;
  total: number;
  prev_num: number | null;
  next_num: number | null;
}