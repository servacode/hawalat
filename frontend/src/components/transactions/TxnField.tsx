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
    <p className="flex items-center gap-2 text-sm">
      <Icon className="size-4 shrink-0 text-brand" aria-hidden="true" />
      <span className="shrink-0 text-muted">{label}:</span>
      <span className="min-w-0 truncate font-medium">{value}</span>
    </p>
  );
}
