"use client";

/** سجل حركات المكتب الصغير مع فلتر (الجزء 3-ج). */

import { CircleCheck, CircleX, FileSpreadsheet, FileText, HandCoins, Hourglass, PackageCheck, RefreshCw, Undo2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, EmptyState, Input, Skeleton, TBody, TD, TH, THead, TR, Table, ViewToggle, useViewMode, type BadgeStatus } from "@/components/ui";
import { StatusFilterCards, type StatusCardDef } from "@/components/transactions/StatusFilterCards";
import { authedApi, authedDownload } from "@/lib/authedApi";
import { formatDateTime, formatMoney } from "@/lib/format";

interface Txn {
  id: number; reference_code: string; sender: string; beneficiary: string;
  amount: string; currency_received: string; destination: string;
  fee_charged: string | null;
  approval_status: "pending" | "accepted" | "cancelled" | "reversed";
  payment_status: "paid" | "unpaid";
  delivery_status: "delivered" | "not_delivered";
  created_at: string;
}

const approvalBadge: Record<Txn["approval_status"], BadgeStatus> = {
  pending: "pending", accepted: "accepted", cancelled: "cancelled", reversed: "reversed",
};

// كروت الحالات الذكية: إحصائية وفلتر معاً — الضغط يفلتر وضغطة ثانية تلغي
const STATUS_CARDS: StatusCardDef<Txn>[] = [
  { key: "pending", label: "قيد الانتظار", icon: Hourglass, tone: "warning", match: (t) => t.approval_status === "pending" },
  { key: "accepted", label: "مقبولة", icon: CircleCheck, tone: "success", match: (t) => t.approval_status === "accepted" },
  { key: "paid", label: "مدفوعة", icon: HandCoins, tone: "info", match: (t) => t.payment_status === "paid" },
  { key: "delivered", label: "تم التسليم", icon: PackageCheck, tone: "brand", match: (t) => t.delivery_status === "delivered" },
  { key: "cancelled", label: "مرفوضة", icon: CircleX, tone: "danger", match: (t) => t.approval_status === "cancelled" },
  { key: "reversed", label: "معكوسة", icon: Undo2, tone: "accent", match: (t) => t.approval_status === "reversed" },
];

// خرائط الكرت النشط → فلاتر الخادم (للتصدير المطابق للعرض)
function cardToServerParams(key: string): string {
  if (key === "paid") return "payment=paid";
  if (key === "delivered") return "delivery=delivered";
  if (key) return `approval=${key}`;
  return "";
}

export default function MyTransactionsPage() {
  const [txns, setTxns] = useState<Txn[] | null>(null);
  const [q, setQ] = useState("");
  const [approval, setApproval] = useState("");

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    authedApi<Txn[]>(`/api/my/transactions/?${params}`).then(setTxns).catch(() => {});
  }, [q]);
  useEffect(load, [load]);

  // الفلترة بالحالة محلياً — حتى تبقى أرقام الكروت شاملة دائماً
  const activeDef = STATUS_CARDS.find((d) => d.key === approval);
  const shown = txns && activeDef ? txns.filter(activeDef.match) : txns;
  const [view, setView] = useViewMode();

  function exportFile(fmt: "xlsx" | "pdf") {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    const extra = cardToServerParams(approval);
    const qs = [params.toString(), extra, `export=${fmt}`].filter(Boolean).join("&");
    authedDownload(`/api/my/transactions/?${qs}`, `سجل-الحركات.${fmt}`);
  }

  return (
    <div className="flex flex-col gap-4">
      <StatusFilterCards items={txns ?? []} defs={STATUS_CARDS} active={approval} onChange={setApproval} />

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-48 flex-1">
          <Input label="بحث" placeholder="مرجع / مرسِل / مستفيد / وجهة" value={q}
            onChange={(e) => setQ(e.target.value)} />
        </div>
        <Button variant="ghost" onClick={load}><RefreshCw className="size-4" />تحديث</Button>
        <Button variant="accent" onClick={() => exportFile("xlsx")}><FileSpreadsheet className="size-4" />Excel</Button>
        <Button variant="accent" onClick={() => exportFile("pdf")}><FileText className="size-4" />PDF</Button>
        <ViewToggle mode={view} onChange={setView} />
      </div>

      {!shown ? (
        <Skeleton className="h-64" />
      ) : shown.length === 0 ? (
        <EmptyState title="لا نتائج" />
      ) : view === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((t) => (
            <Card key={t.id}>
              <CardBody className="flex flex-col gap-2 py-3.5">
                <div className="flex items-center justify-between gap-2">
                  <span dir="ltr" className="tnum text-sm text-muted">{t.reference_code}</span>
                  <Badge status={approvalBadge[t.approval_status]} />
                </div>
                <p className="tnum text-lg font-bold">{formatMoney(t.amount, t.currency_received)}</p>
                <div className="flex flex-col gap-1 text-sm">
                  <p><span className="text-muted">المستفيد:</span> {t.beneficiary}</p>
                  {t.sender && <p><span className="text-muted">المرسِل:</span> {t.sender}</p>}
                  <p><span className="text-muted">الوجهة:</span> {t.destination}</p>
                  <p><span className="text-muted">الأجور:</span> {t.fee_charged ? formatMoney(t.fee_charged) : "—"}</p>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="tnum text-muted">{formatDateTime(t.created_at)}</span>
                  {t.payment_status === "paid" && <Badge status="paid" />}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>المرجع</TH><TH>التاريخ</TH><TH>المرسِل</TH><TH>المستفيد</TH>
              <TH>المبلغ</TH><TH>الأجور</TH><TH>الوجهة</TH><TH>القبول</TH><TH>الدفع</TH>
            </TR>
          </THead>
          <TBody>
            {shown.map((t) => (
              <TR key={t.id}>
                <TD className="tnum text-sm text-muted">{t.reference_code}</TD>
                <TD className="tnum text-sm">{formatDateTime(t.created_at)}</TD>
                <TD>{t.sender}</TD>
                <TD>{t.beneficiary}</TD>
                <TD className="tnum font-bold">{formatMoney(t.amount, t.currency_received)}</TD>
                <TD className="tnum">{t.fee_charged ? formatMoney(t.fee_charged) : "—"}</TD>
                <TD>{t.destination}</TD>
                <TD><Badge status={approvalBadge[t.approval_status]} /></TD>
                <TD>{t.payment_status === "paid" ? <Badge status="paid" /> : <span className="text-muted">—</span>}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
