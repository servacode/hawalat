import { cn } from "@/lib/cn";
import type { HTMLAttributes } from "react";

/** حالات الحركة الموحّدة — الأسماء مركزية وتُستخدم في كل النظام */
export type BadgeStatus =
  | "pending" // قيد الانتظار
  | "accepted" // مقبولة
  | "cancelled" // ملغية
  | "paid" // مدفوعة
  | "delivered" // تم التسليم
  | "reversed"; // معكوسة

const styles: Record<BadgeStatus, string> = {
  pending: "text-warning bg-warning/15",
  accepted: "text-success bg-success/15",
  cancelled: "text-danger bg-danger/15",
  paid: "text-info bg-info/15",
  delivered: "text-brand-700 bg-brand/15",
  reversed: "text-muted bg-muted/15",
};

export const badgeLabels: Record<BadgeStatus, string> = {
  pending: "قيد الانتظار",
  accepted: "مقبولة",
  cancelled: "ملغية",
  paid: "مدفوعة",
  delivered: "تم التسليم",
  reversed: "معكوسة",
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status: BadgeStatus;
}

export function Badge({ status, className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium",
        "before:size-1.5 before:rounded-full before:bg-current",
        styles[status],
        className,
      )}
      {...props}
    >
      {children ?? badgeLabels[status]}
    </span>
  );
}
