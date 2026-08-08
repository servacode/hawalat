"use client";

/**
 * تبديل ذكي بين الجدول والكروت (مركزي): على الجوال الافتراضي كروت
 * (لا سحب أفقياً)، وعلى الشاشات الواسعة جدول — والمستخدم يبدّل بزر.
 */

import { LayoutGrid, Table2 } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";

export type ViewMode = "table" | "cards";

export function useViewMode(): [ViewMode, (m: ViewMode) => void] {
  // نبدأ بالجدول ثم نضبط حسب عرض الشاشة بعد الترطيب (لا وميض SSR)
  const [mode, setMode] = useState<ViewMode>("table");
  useEffect(() => {
    if (window.innerWidth < 768) setMode("cards");
  }, []);
  return [mode, setMode];
}

export function ViewToggle({
  mode,
  onChange,
}: {
  mode: ViewMode;
  onChange: (m: ViewMode) => void;
}) {
  const base =
    "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-brand";
  return (
    <div className="flex items-center gap-1 rounded-xl border border-border bg-surface p-1" role="group" aria-label="طريقة العرض">
      <button
        type="button"
        aria-pressed={mode === "table"}
        onClick={() => onChange("table")}
        className={cn(base, mode === "table" ? "bg-brand text-white" : "text-muted hover:text-ink")}
      >
        <Table2 className="size-4" /> جدول
      </button>
      <button
        type="button"
        aria-pressed={mode === "cards"}
        onClick={() => onChange("cards")}
        className={cn(base, mode === "cards" ? "bg-brand text-white" : "text-muted hover:text-ink")}
      >
        <LayoutGrid className="size-4" /> كروت
      </button>
    </div>
  );
}
