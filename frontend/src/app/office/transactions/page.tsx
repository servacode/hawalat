"use client";

/** سجل حركات المكتب الكبير (الجزء 11): كل المنفَّذ + فلتر احترافي + مدفوعة/تسليم/عكس. */

import { Building2, CalendarDays, Check, CircleCheck, CircleX, Coins, FileSpreadsheet, FileText, HandCoins, MapPin, PackageCheck, Pencil, RefreshCw, Undo2, UserCheck, Wallet } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, EmptyState, Input, Modal, Pagination, Skeleton, TBody, TD, TH, THead, TR, Table, ViewToggle, usePagination, useViewMode, type BadgeStatus } from "@/components/ui";
import { StatusFilterCards, type StatusCardDef } from "@/components/transactions/StatusFilterCards";
import { DoneCheck } from "@/components/transactions/DoneCheck";
import { TxnField } from "@/components/transactions/TxnField";
import { authedApi, authedDownload } from "@/lib/authedApi";
import { formatDate, formatMoney } from "@/lib/format";

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

// كروت الحالات الذكية: إحصائية وفلتر معاً — الضغط يفلتر وضغطة ثانية تلغي
const STATUS_CARDS: StatusCardDef<Txn>[] = [
  { key: "accepted", label: "مقبولة", icon: CircleCheck, tone: "success", match: (t) => t.approval_status === "accepted" },
  { key: "paid", label: "مدفوعة", icon: HandCoins, tone: "info", match: (t) => t.payment_status === "paid" },
  { key: "delivered", label: "تم التسليم", icon: PackageCheck, tone: "brand", match: (t) => t.delivery_status === "delivered" },
  { key: "cancelled", label: "مرفوضة", icon: CircleX, tone: "danger", match: (t) => t.approval_status === "cancelled" },
  { key: "reversed", label: "معكوسة", icon: Undo2, tone: "accent", match: (t) => t.approval_status === "reversed" },
];

// الكرت النشط → فلاتر الخادم (للتصدير المطابق للعرض)
function cardToServerParams(key: string): string {
  if (key === "paid") return "payment=paid";
  if (key === "delivered") return "delivery=delivered";
  if (key) return `approval=${key}`;
  return "";
}

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
    authedApi<Txn[]>(`/api/office/transactions/history/?${params}`)
      .then(setTxns)
      .catch(() => {});
  }, [q]);
  useEffect(load, [load]);

  // الفلترة بالحالة محلياً — حتى تبقى أرقام الكروت شاملة دائماً
  const activeDef = STATUS_CARDS.find((d) => d.key === approval);
  const shown = txns && activeDef ? txns.filter(activeDef.match) : txns;
  const [view, setView] = useViewMode();
  const pager = usePagination(shown ?? [], 9);

  function exportFile(fmt: "xlsx" | "pdf") {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    const extra = cardToServerParams(approval);
    const qs = [params.toString(), extra, `export=${fmt}`].filter(Boolean).join("&");
    authedDownload(`/api/office/transactions/history/?${qs}`, `سجل-الحركات.${fmt}`);
  }

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

  function rowActions(t: Txn, compact = false) {
    if (t.approval_status !== "accepted") return null;
    if (t.delivery_status === "delivered") {
      // التسليم نهائي مطلق — الزبون استلم وذهب: لا أي إجراء
      return <span className="whitespace-nowrap text-sm text-muted">سُلّمت — نهائي</span>;
    }
    if (compact) {
      // أزرار أيقونية بسطر واحد للجدول (ملاحظة 30) — الاسم tooltip
      const iconBtn =
        "flex size-8 items-center justify-center rounded-lg border border-border text-muted transition-colors hover:border-brand hover:text-brand-700 disabled:opacity-40";
      return (
        <div className="flex flex-nowrap items-center gap-1.5">
          {t.payment_status !== "paid" && (
            <button type="button" title="مدفوعة" aria-label="مدفوعة" className={iconBtn}
              disabled={busy === t.id} onClick={() => act(t, "pay")}>
              <HandCoins className="size-4" />
            </button>
          )}
          <button type="button" title="تم التسليم" aria-label="تم التسليم" className={iconBtn}
            disabled={busy === t.id} onClick={() => act(t, "deliver")}>
            <PackageCheck className="size-4" />
          </button>
          {t.payment_status !== "paid" && (
            <button type="button" title="تعديل" aria-label="تعديل" className={iconBtn}
              disabled={busy === t.id} onClick={() => openEdit(t)}>
              <Pencil className="size-4" />
            </button>
          )}
          <button type="button" title="عكس" aria-label="عكس"
            className="flex size-8 items-center justify-center rounded-lg border border-danger/40 text-danger transition-colors hover:bg-danger hover:text-white disabled:opacity-40"
            disabled={busy === t.id} onClick={() => act(t, "reverse")}>
            <Undo2 className="size-4" />
          </button>
        </div>
      );
    }
    return (
      <div className="flex flex-wrap gap-1.5">
        {t.payment_status !== "paid" && (
          <Button size="sm" variant="ghost" disabled={busy === t.id} onClick={() => act(t, "pay")}>
            <HandCoins className="size-4" />مدفوعة
          </Button>
        )}
        <Button size="sm" variant="ghost" disabled={busy === t.id} onClick={() => act(t, "deliver")}>
          <PackageCheck className="size-4" />تم التسليم
        </Button>
        {t.payment_status !== "paid" && (
          <Button size="sm" variant="ghost" disabled={busy === t.id} onClick={() => openEdit(t)}>
            <Pencil className="size-4" />تعديل
          </Button>
        )}
        <Button size="sm" variant="danger" disabled={busy === t.id} onClick={() => act(t, "reverse")}>
          <Undo2 className="size-4" />عكس
        </Button>
      </div>
    );
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

      <p className="text-sm text-muted">
        ملاحظة: «تم التسليم» نهائي — لا عكس ولا تعديل بعده، فلا تعلّمه إلا بعد تأكد الاستلام.
        و«مدفوعة» تعني قبض المبلغ + الأجور نقداً في صندوق المحل.
      </p>

      {!shown ? (
        <Skeleton className="h-64" />
      ) : shown.length === 0 ? (
        <EmptyState title="لا حركات منفَّذة بعد" />
      ) : view === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {pager.slice.map((t) => (
            <Card key={t.id}>
              <CardBody className="flex flex-col gap-2.5 py-3.5">
                {/* الحالات يميناً والمرجع أعلى اليسار (ملاحظة 23) */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge status={approvalBadge[t.approval_status]} />
                    {t.payment_status === "paid" && <Badge status="paid" />}
                    {t.delivery_status === "delivered" && <Badge status="delivered" />}
                  </div>
                  <span dir="ltr" className="tnum ms-auto text-sm text-muted">{t.reference_code}</span>
                </div>
                <p className="tnum text-xl font-bold">{formatMoney(t.amount, t.currency_received)}</p>
                <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface-2/30">
                  <TxnField icon={Building2} label="من مكتب" value={t.created_by_name} />
                  <TxnField icon={UserCheck} label="المستفيد" value={t.beneficiary} />
                  <TxnField icon={MapPin} label="الوجهة" value={t.destination} />
                  <TxnField icon={Coins} label="الأجور"
                    value={t.fee_cost ? `${formatMoney(t.fee_cost)} / ${formatMoney(t.fee_charged ?? 0)} ${t.currency_received}` : "—"} />
                  <TxnField icon={Wallet} label="الصندوق" value={t.box_name ?? "—"} />
                  <TxnField icon={CalendarDays} label="التاريخ"
                    value={<span className="tnum">{formatDate(t.created_at)}</span>} />
                </div>
                {rowActions(t)}
              </CardBody>
            </Card>
          ))}
        </div>
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>المرجع</TH><TH>من مكتب</TH><TH>المستفيد</TH><TH>المبلغ</TH>
              <TH>الأجور</TH><TH>الصندوق</TH><TH>الحالة</TH>
              <TH className="text-center">مدفوعة</TH><TH className="text-center">التسليم</TH>
              <TH>إجراءات</TH>
            </TR>
          </THead>
          <TBody>
            {pager.slice.map((t) => (
              <TR key={t.id}>
                <TD>
                  <span dir="ltr" className="tnum block text-sm">{t.reference_code}</span>
                  <span className="tnum block text-xs text-muted">{formatDate(t.created_at)}</span>
                </TD>
                <TD className="whitespace-nowrap">{t.created_by_name}</TD>
                <TD>{t.beneficiary}</TD>
                <TD className="tnum whitespace-nowrap font-bold">{formatMoney(t.amount, t.currency_received)}</TD>
                <TD className="tnum whitespace-nowrap">
                  {t.fee_cost ? `${formatMoney(t.fee_cost)} / ${formatMoney(t.fee_charged ?? 0)} ${t.currency_received}` : "—"}
                </TD>
                <TD className="whitespace-nowrap">{t.box_name ?? "—"}</TD>
                <TD><Badge status={approvalBadge[t.approval_status]} /></TD>
                <TD><DoneCheck done={t.payment_status === "paid"} label="مدفوعة" /></TD>
                <TD><DoneCheck done={t.delivery_status === "delivered"} label="تم التسليم" /></TD>
                <TD>{rowActions(t, true)}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
      <Pagination page={pager.page} pages={pager.pages} total={pager.total} onChange={pager.setPage} />

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
            <Button type="submit"><Check className="size-4" />تطبيق التعديل</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
