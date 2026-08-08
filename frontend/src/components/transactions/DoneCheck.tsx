import { CircleCheck } from "lucide-react";

/**
 * إشارة إنجاز داخل الجداول (ملاحظة 31): صح أخضر يظهر فقط بعد تنفيذ الإجراء
 * (مدفوعة / تم التسليم) — وقبله شرطة باهتة بدل النص المتكرر.
 */
export function DoneCheck({ done, label }: { done: boolean; label: string }) {
  if (!done) {
    return <span aria-hidden="true" className="block text-center text-muted/50">—</span>;
  }
  return <CircleCheck aria-label={label} className="mx-auto size-5 text-success" />;
}
