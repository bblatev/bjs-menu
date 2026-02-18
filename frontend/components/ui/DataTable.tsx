'use client';
import { useState } from 'react';

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  searchable?: boolean;
  searchPlaceholder?: string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

export default function DataTable<T extends Record<string, any>>({
  data,
  columns,
  searchable,
  searchPlaceholder,
  onRowClick,
  emptyMessage,
}: DataTableProps<T>) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  let filtered = data;
  if (searchable && search) {
    const q = search.toLowerCase();
    filtered = data.filter((item) =>
      columns.some((col) => String(item[col.key] ?? '').toLowerCase().includes(q))
    );
  }
  if (sortKey) {
    filtered = [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div>
      {searchable && (
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={searchPlaceholder || 'Search...'}
          className="mb-4 w-full px-3 py-2 border rounded dark:bg-surface-800 dark:border-surface-600"
          aria-label="Search table"
        />
      )}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse" role="grid">
          <thead>
            <tr className="bg-gray-50 dark:bg-surface-800 border-b dark:border-surface-700">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-surface-300 cursor-pointer select-none"
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                  aria-sort={sortKey === col.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  {col.header} {sortKey === col.key && (sortDir === 'asc' ? '↑' : '↓')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500">
                  {emptyMessage || 'No data'}
                </td>
              </tr>
            ) : (
              filtered.map((item, i) => (
                <tr
                  key={i}
                  onClick={() => onRowClick?.(item)}
                  className={`border-b dark:border-surface-700 hover:bg-gray-50 dark:hover:bg-surface-800 ${onRowClick ? 'cursor-pointer' : ''}`}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={(e) => e.key === 'Enter' && onRowClick?.(item)}
                  role={onRowClick ? 'button' : undefined}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-sm">
                      {col.render ? col.render(item) : String(item[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
