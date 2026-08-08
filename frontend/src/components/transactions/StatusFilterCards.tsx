"use client";

/**
 * كروت الحالات الذكية (مركزية): إحصائية وفلتر معاً —
 * كل كرت يعرض عدد حركات حالته، والضغط عليه يفلتر الجدول (وضغطة ثانية تلغي).
 */

import type { LucideIcon } from "lucide-react";
import { Layers } from "lucide-react";
import { cn } from "@/lib/cn";

export interface StatusCardDef<T> {
  key: string;
  label: string;
  icon: LucideIcon;
  tone: "brand" | "success" | "warning" | "danger" | "info" | "accent";
  match: (item: T) => boolean;
}

const TONE: Record<StatusCardDef<unknown>["tone"], string> = {
  brand: "bg-brand/10 text-brand-700",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
  info: "bg-info/10 text-info",
  accent: "bg-accent/10 text-accent",
};

export function StatusFilterCards<T>({
  items,
  defs,
  active,
  onChange,
}: {
  items: T[];
  defs: StatusCardDef<T>[];
  /** مفتاح الحالة النشطة — "" تعني الكل */
  active: string;
  onChange: (key: string) => void;
}) {
  const all: StatusCardDef<T> = {
    key: "",
    label: "الكل",
    icon: Layers,
    tone: "brand",
    match: () => true,
  };
  return (
    <div className="flex flex-wrap gap-2.5">
      {[all, ...defs].map((d) => {
        const Icon = d.icon;
        const count = items.filter(d.match).length;
        const isActive = active === d.key;
        return (
          <button
            key={d.key || "all"}
            type="button"
            onClick={() => onChange(isActive ? "" : d.key)}
            aria-pressed={isActive}
            className={cn(
              "flex min-w-36 flex-1 items-center gap-3 rounded-xl border bg-surface p-3 text-start shadow-sm transition-all",
              isActive
                ? "border-brand ring-2 ring-brand/30"
                : "border-border hover:border-brand/50",
            )}
          >
            <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", TONE[d.tone])}>
              <Icon className="size-4.5" aria-hidden="true" />
            </span>
            <span className="min-w-0 leading-tight">
              <span className="tnum block text-lg font-bold">{count}</span>
              <span className="block truncate text-xs text-muted">{d.label}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
