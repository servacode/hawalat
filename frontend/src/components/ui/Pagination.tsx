"use client";

/**
 * باجينيشن مركزي (ملاحظة 24): تقسيم القوائم الطويلة صفحات — سابق/تالي + العدّاد.
 * hook للتقطيع + مكوّن أزرار، يعملان مع أي مصفوفة.
 */

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

export function usePagination<T>(items: T[], perPage = 10) {
  const [page, setPage] = useState(1);
  const pages = Math.max(1, Math.ceil(items.length / perPage));
  // عودة للصفحة الأولى عند تغيّر البيانات أو الفلاتر
  useEffect(() => {
    setPage(1);
  }, [items.length]);
  const safePage = Math.min(page, pages);
  const slice = useMemo(
    () => items.slice((safePage - 1) * perPage, safePage * perPage),
    [items, safePage, perPage],
  );
  return { page: safePage, setPage, pages, slice, total: items.length };
}

export function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (p: number) => void;
}) {
  if (pages <= 1) return null;
  const btn =
    "flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm transition-colors hover:border-brand/50 disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <div className="flex items-center justify-between gap-3">
      <button type="button" className={btn} disabled={page <= 1} onClick={() => onChange(page - 1)}>
        <ChevronRight className="size-4" /> السابق
      </button>
      <p className="tnum text-sm text-muted">
        صفحة {page} من {pages} · {total} سجلاً
      </p>
      <button
        type="button"
        className={btn}
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        التالي <ChevronLeft className="size-4" />
      </button>
    </div>
  );
}
