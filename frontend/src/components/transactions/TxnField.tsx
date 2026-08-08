import type { LucideIcon } from "lucide-react";

/** حقل بيانات داخل كرت الحركة (ملاحظة 21): أيقونة معبّرة + اسم + قيمة. */
export function TxnField({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
      <span className="flex shrink-0 items-center gap-2 text-muted">
        <Icon className="size-4 shrink-0 text-brand" aria-hidden="true" />
        {label}
      </span>
      <span className="min-w-0 truncate text-end font-medium">{value}</span>
    </div>
  );
}
