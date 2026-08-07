/**
 * حوالات — أدوات التنسيق المركزية (ق1)
 * كل عرض لمبلغ/تاريخ في النظام يمرّ من هنا حصراً — لا تنسيق يدوي في الصفحات.
 */

/** تنسيق مبلغ مالي: فواصل آلاف + منزلتان + إشارة واضحة */
export function formatMoney(value: number | string, currency?: string): string {
  const n = typeof value === "string" ? Number(value) : value;
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(n));
  const sign = n < 0 ? "−" : "";
  return currency ? `${sign}${formatted} ${currency}` : `${sign}${formatted}`;
}

/** دلالة الرصيد وفق اصطلاح الدورة: موجب = لنا، سالب = علينا */
export function balanceTone(value: number | string): "pos" | "neg" | "neutral" {
  const n = typeof value === "string" ? Number(value) : value;
  if (n > 0) return "pos";
  if (n < 0) return "neg";
  return "neutral";
}

/** تنسيق تاريخ/وقت موحّد (ميلادي بأرقام لاتينية للوضوح المحاسبي) */
export function formatDateTime(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}
