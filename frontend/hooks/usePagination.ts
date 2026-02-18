'use client';
import { useState, useMemo } from 'react';

interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
}

export function usePagination<T>(data: T[], options: UsePaginationOptions = {}) {
  const { initialPage = 1, initialPageSize = 25 } = options;
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const totalPages = Math.max(1, Math.ceil(data.length / pageSize));

  const paginatedData = useMemo(() => {
    const start = (page - 1) * pageSize;
    return data.slice(start, start + pageSize);
  }, [data, page, pageSize]);

  const goToPage = (p: number) => {
    setPage(Math.max(1, Math.min(p, totalPages)));
  };

  const changePageSize = (size: number) => {
    setPageSize(size);
    setPage(1);
  };

  return {
    page,
    pageSize,
    totalPages,
    paginatedData,
    goToPage,
    changePageSize,
    totalItems: data.length,
  };
}
