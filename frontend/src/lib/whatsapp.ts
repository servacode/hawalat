import { formatMoney } from "@/lib/format";

/**
 * حوالات — قالب رسالة الواتساب المركزي (الجزء 3-أ)
 * الوضع الافتراضي: رابط (يدوي) — يفتح مجموعة المستخدم أو نافذة مشاركة نصية.
 * (وضع البوت الاختياري يُضاف في مرحلة الواتساب.)
 */

export interface TxnMessage {
  reference_code: string;
  sender: string;
  beneficiary: string;
  amount: string;
  currency_received: string;
  currency_delivered: string;
  destination: string;
}

/** نص الحركة وفق البيانات بالترتيب (المشهد 2-أ) */
export function buildTransactionMessage(t: TxnMessage): string {
  const lines = [
    `🧾 حركة جديدة — ${t.reference_code}`,
    ...(t.sender ? [`المرسِل: ${t.sender}`] : []),
    `المستفيد: ${t.beneficiary}`,
    `المبلغ: ${formatMoney(t.amount)} ${t.currency_received}`,
  ];
  if (t.currency_delivered !== t.currency_received) {
    lines.push(`التسليم بعملة: ${t.currency_delivered}`);
  }
  lines.push(`الوجهة: ${t.destination}`);
  return lines.join("\n");
}

/**
 * يفتح واتساب للإرسال:
 * - مع رابط مجموعة: يَنسخ النص ثم يفتح المجموعة (واتساب لا يدعم نصاً مسبقاً للمجموعات).
 * - بدونه: يفتح نافذة مشاركة wa.me بالنص الجاهز.
 */
export async function sendToWhatsApp(text: string, groupLink?: string | null) {
  if (groupLink) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* تجاهل — سيلصق المستخدم يدوياً */
    }
    window.open(groupLink, "_blank", "noopener");
    return "copied" as const;
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
  return "shared" as const;
}

// ---------------------------------------------------------------- المطابقة

export interface ReconciliationRow {
  currency: string;
  previous: string;
  debits: string;
  credits: string;
  balance: string;
}

/** نص المطابقة (المشهد 4): رصيد سابق + حركات الفترة + الصافي لكل عملة. */
export function buildReconciliationMessage(
  officeName: string,
  officeCode: string,
  rows: ReconciliationRow[],
  lastAt?: string | null,
): string {
  const lines = [`📊 مطابقة حساب — ${officeName} (${officeCode})`];
  if (lastAt) lines.push(`منذ آخر مطابقة: ${new Date(lastAt).toLocaleString("en-GB")}`);
  for (const r of rows) {
    const bal = Number(r.balance);
    const label =
      bal > 0 ? `عليكم ${formatMoney(bal)}` : bal < 0 ? `لكم ${formatMoney(-bal)}` : "متوازن";
    lines.push(
      `— ${r.currency}: سابق ${formatMoney(r.previous)} · لكم ${formatMoney(r.credits)} · عليكم ${formatMoney(r.debits)} ⇐ ${label}`,
    );
  }
  lines.push("(كشف دوري — لا يُصفّر الحسابات)");
  return lines.join("\n");
}
