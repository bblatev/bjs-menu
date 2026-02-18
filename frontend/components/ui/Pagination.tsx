'use client';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
}

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  onPageSizeChange,
}: PaginationProps) {
  const maxVisible = 5;
  let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  const end = Math.min(totalPages, start + maxVisible - 1);
  if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);

  const pages: number[] = [];
  for (let i = start; i <= end; i++) pages.push(i);

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between mt-4" role="navigation" aria-label="Pagination">
      <div className="flex items-center gap-2">
        {onPageSizeChange && pageSize && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="border rounded px-2 py-1 text-sm dark:bg-surface-800 dark:border-surface-600"
            aria-label="Items per page"
          >
            {[10, 25, 50, 100].map((s) => (
              <option key={s} value={s}>
                {s} per page
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="px-3 py-1 rounded border disabled:opacity-50 dark:border-surface-600"
          aria-label="Previous page"
        >
          &laquo;
        </button>
        {start > 1 && (
          <>
            <button onClick={() => onPageChange(1)} className="px-3 py-1 rounded border dark:border-surface-600">
              1
            </button>
            <span className="px-1">...</span>
          </>
        )}
        {pages.map((p) => (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`px-3 py-1 rounded border dark:border-surface-600 ${
              p === currentPage ? 'bg-blue-600 text-white border-blue-600' : ''
            }`}
            aria-current={p === currentPage ? 'page' : undefined}
          >
            {p}
          </button>
        ))}
        {end < totalPages && (
          <>
            <span className="px-1">...</span>
            <button onClick={() => onPageChange(totalPages)} className="px-3 py-1 rounded border dark:border-surface-600">
              {totalPages}
            </button>
          </>
        )}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="px-3 py-1 rounded border disabled:opacity-50 dark:border-surface-600"
          aria-label="Next page"
        >
          &raquo;
        </button>
      </div>
    </div>
  );
}
