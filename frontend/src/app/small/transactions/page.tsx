"use client";

/** سجل حركات المكتب الصغير مع فلتر (الجزء 3-ج). */

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, EmptyState, Input, Select, Skeleton, TBody, TD, TH, THead, TR, Table, type BadgeStatus } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
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

export default function MyTransactionsPage() {
  const [txns, setTxns] = useState<Txn[] | null>(null);
  const [q, setQ] = useState("");
  const [approval, setApproval] = useState("");

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (approval) params.set("approval", approval);
    authedApi<Txn[]>(`/api/my/transactions/?${params}`).then(setTxns).catch(() => {});
  }, [q, approval]);
  useEffect(load, [load]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-48 flex-1">
          <Input label="بحث" placeholder="مرجع / مرسِل / مستفيد / وجهة" value={q}
            onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="min-w-40">
          <Select label="الحالة" placeholder="الكل" value={approval}
            onChange={(e) => setApproval(e.target.value)}
            options={[
              { value: "pending", label: "قيد الانتظار" },
              { value: "accepted", label: "مقبولة" },
              { value: "cancelled", label: "ملغية" },
              { value: "reversed", label: "معكوسة" },
            ]} />
        </div>
        <Button variant="ghost" onClick={load}>تحديث</Button>
      </div>

      {!txns ? (
        <Skeleton className="h-64" />
      ) : txns.length === 0 ? (
        <EmptyState title="لا نتائج" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>المرجع</TH><TH>التاريخ</TH><TH>المرسِل</TH><TH>المستفيد</TH>
              <TH>المبلغ</TH><TH>الأجور</TH><TH>الوجهة</TH><TH>القبول</TH><TH>الدفع</TH>
            </TR>
          </THead>
          <TBody>
            {txns.map((t) => (
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
