"use client";

/** سجل حركات المكتب الكبير (الجزء 11): كل المنفَّذ + فلتر احترافي + مدفوعة/تسليم/عكس. */

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, EmptyState, Input, Modal, Select, Skeleton, TBody, TD, TH, THead, TR, Table, type BadgeStatus } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime, formatMoney } from "@/lib/format";

interface Txn {
  id: number; reference_code: string; sender: string; beneficiary: string;
  amount: string; currency_received: string; destination: string;
  fee_cost: string | null; fee_charged: string | null; box_name: string | null;
  created_by_name: string; created_by_code: string;
  approval_status: "accepted" | "cancelled" | "reversed";
  payment_status: "paid" | "unpaid";
  delivery_status: "delivered" | "not_delivered";
  created_at: string;
}

const approvalBadge: Record<Txn["approval_status"], BadgeStatus> = {
  accepted: "accepted", cancelled: "cancelled", reversed: "reversed",
};

export default function OfficeHistoryPage() {
  const [txns, setTxns] = useState<Txn[] | null>(null);
  const [q, setQ] = useState("");
  const [approval, setApproval] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [editFor, setEditFor] = useState<Txn | null>(null);
  const [editForm, setEditForm] = useState({ amount: "", fee_cost: "", fee_charged: "" });
  const [editError, setEditError] = useState<string | null>(null);

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (approval) params.set("approval", approval);
    authedApi<Txn[]>(`/api/office/transactions/history/?${params}`)
      .then(setTxns)
      .catch(() => {});
  }, [q, approval]);
  useEffect(load, [load]);

  function openEdit(t: Txn) {
    setEditFor(t);
    setEditForm({ amount: t.amount, fee_cost: t.fee_cost ?? "", fee_charged: t.fee_charged ?? "" });
    setEditError(null);
  }

  async function submitEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editFor) return;
    setEditError(null);
    try {
      await authedApi(`/api/office/transactions/${editFor.id}/edit/`, {
        method: "POST", body: editForm,
      });
      setEditFor(null);
      load();
    } catch (err) {
      const detail = (err as { data?: { detail?: string } })?.data?.detail;
      setEditError(detail ?? "تعذر التعديل — اعكس القبض أولاً إن كانت مدفوعة.");
    }
  }

  async function act(t: Txn, action: "pay" | "deliver" | "reverse") {
    setBusy(t.id);
    try {
      await authedApi(`/api/office/transactions/${t.id}/${action}/`, { method: "POST" });
      load();
    } catch {
      /* الخطأ يظهر بإعادة التحميل */
    } finally {
      setBusy(null);
    }
  }

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
        <EmptyState title="لا حركات منفَّذة بعد" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>المرجع</TH><TH>التاريخ</TH><TH>من مكتب</TH><TH>المستفيد</TH>
              <TH>المبلغ</TH><TH>الأجور (رأس مال/مستحقة)</TH><TH>الصندوق</TH>
              <TH>القبول</TH><TH>الدفع</TH><TH>التسليم</TH><TH>إجراءات</TH>
            </TR>
          </THead>
          <TBody>
            {txns.map((t) => (
              <TR key={t.id}>
                <TD className="tnum text-sm text-muted">{t.reference_code}</TD>
                <TD className="tnum text-sm">{formatDateTime(t.created_at)}</TD>
                <TD>{t.created_by_name}</TD>
                <TD>{t.beneficiary}</TD>
                <TD className="tnum font-bold">{formatMoney(t.amount, t.currency_received)}</TD>
                <TD className="tnum">
                  {t.fee_cost ? `${formatMoney(t.fee_cost)} / ${formatMoney(t.fee_charged ?? 0)}` : "—"}
                </TD>
                <TD>{t.box_name ?? "—"}</TD>
                <TD><Badge status={approvalBadge[t.approval_status]} /></TD>
                <TD>
                  {t.payment_status === "paid" ? <Badge status="paid" /> : <span className="text-muted">غير مدفوعة</span>}
                </TD>
                <TD>
                  {t.delivery_status === "delivered" ? <Badge status="delivered" /> : <span className="text-muted">—</span>}
                </TD>
                <TD>
                  {t.approval_status === "accepted" && (
                    <div className="flex flex-wrap gap-1.5">
                      {t.payment_status !== "paid" && (
                        <Button size="sm" variant="ghost" disabled={busy === t.id} onClick={() => act(t, "pay")}>
                          مدفوعة
                        </Button>
                      )}
                      {t.delivery_status !== "delivered" && (
                        <Button size="sm" variant="ghost" disabled={busy === t.id} onClick={() => act(t, "deliver")}>
                          تم التسليم
                        </Button>
                      )}
                      {t.payment_status !== "paid" && (
                        <Button size="sm" variant="ghost" disabled={busy === t.id} onClick={() => openEdit(t)}>
                          تعديل
                        </Button>
                      )}
                      <Button size="sm" variant="danger" disabled={busy === t.id} onClick={() => act(t, "reverse")}>
                        عكس
                      </Button>
                    </div>
                  )}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
      <Modal open={editFor !== null} onClose={() => setEditFor(null)}
        title={editFor ? `تعديل ${editFor.reference_code}` : ""}>
        <form onSubmit={submitEdit} className="flex flex-col gap-4">
          <p className="rounded-md bg-warning/10 px-3 py-2 text-sm text-warning">
            التعديل يعكس القيد الأصلي ويعيد ترحيله بالقيم الجديدة — وينعكس على الطرفين.
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            <Input label="المبلغ" type="number" step="0.01" min={0} className="tnum"
              value={editForm.amount}
              onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })} />
            <Input label="رأس مال الأجور" type="number" step="0.01" min={0} className="tnum"
              value={editForm.fee_cost}
              onChange={(e) => setEditForm({ ...editForm, fee_cost: e.target.value })} />
            <Input label="الأجور المستحقة" type="number" step="0.01" min={0} className="tnum"
              value={editForm.fee_charged}
              onChange={(e) => setEditForm({ ...editForm, fee_charged: e.target.value })} />
          </div>
          {editError && <p className="text-sm text-danger">{editError}</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setEditFor(null)}>إلغاء</Button>
            <Button type="submit">تطبيق التعديل</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
