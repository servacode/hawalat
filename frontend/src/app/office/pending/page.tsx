"use client";

/**
 * الحركات الجارية (الجزء 7-ب + المشهد 2-ب):
 * جدول قيد الانتظار، ولكل حركة نافذة معالجة: صندوق + رأس مال الأجور +
 * الأجور المستحقة + سعر الصرف (إن اختلفت العملتان — إلزامي) → قبول/رفض.
 */

import { Building2, CalendarDays, Check, ClipboardCheck, MapPin, UserCheck, UserRound, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, EmptyState, Input, Modal, Select, Skeleton, TBody, TD, TH, THead, TR, Table, ViewToggle, useViewMode } from "@/components/ui";
import { TxnField } from "@/components/transactions/TxnField";
import { authedApi } from "@/lib/authedApi";
import { onWsEvent } from "@/lib/ws";
import { formatDateTime, formatMoney } from "@/lib/format";

interface Txn {
  id: number; reference_code: string; sender: string; beneficiary: string;
  amount: string; currency_received: string; currency_delivered: string;
  destination: string; created_by_name: string; created_by_code: string;
  created_at: string;
}
interface Box { id: number; name: string; number: string; currencies: string[] }

export default function PendingPage() {
  const [txns, setTxns] = useState<Txn[] | null>(null);
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [processing, setProcessing] = useState<Txn | null>(null);
  const [form, setForm] = useState({ box: "", fee_cost: "", fee_charged: "", exchange_rate: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useViewMode();

  const load = useCallback(() => {
    authedApi<Txn[]>("/api/office/transactions/pending/").then(setTxns).catch(() => {});
    authedApi<{ results?: Box[] } | Box[]>("/api/office/boxes/")
      .then((d) => setBoxes(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);
  useEffect(
    () => onWsEvent((e) => {
      if (e.kind === "refresh" && e.scope === "pending") load();
      if (e.kind === "notification" && e.ntype === "txn_new") load();
    }),
    [load],
  );

  const dual = processing && processing.currency_received !== processing.currency_delivered;
  const eligibleBoxes = processing
    ? boxes.filter((b) => b.currencies.includes(processing.currency_delivered))
    : [];

  function openProcess(t: Txn) {
    setProcessing(t);
    setForm({ box: "", fee_cost: "", fee_charged: "", exchange_rate: "" });
    setError(null);
  }

  async function act(action: "approve" | "reject") {
    if (!processing) return;
    setBusy(true);
    setError(null);
    try {
      if (action === "approve") {
        await authedApi(`/api/office/transactions/${processing.id}/approve/`, {
          method: "POST",
          body: {
            box: Number(form.box),
            fee_cost: form.fee_cost,
            fee_charged: form.fee_charged,
            ...(dual ? { exchange_rate: form.exchange_rate } : {}),
          },
        });
      } else {
        await authedApi(`/api/office/transactions/${processing.id}/reject/`, { method: "POST" });
      }
      setProcessing(null);
      load();
    } catch (e) {
      const detail = (e as { data?: { detail?: string } })?.data?.detail;
      setError(detail ?? "تعذر تنفيذ الإجراء — تأكد من البيانات.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <ViewToggle mode={view} onChange={setView} />
      </div>
      {!txns ? (
        <Skeleton className="h-64" />
      ) : txns.length === 0 ? (
        <EmptyState title="لا حركات قيد الانتظار" description="عند وصول حركة جديدة ستظهر هنا فوراً." />
      ) : view === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {txns.map((t) => (
            <Card key={t.id}>
              <CardBody className="flex flex-col gap-2.5 py-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge status="pending" />
                  <span dir="ltr" className="tnum ms-auto text-sm text-muted">{t.reference_code}</span>
                </div>
                <p className="tnum text-xl font-bold">{formatMoney(t.amount, t.currency_received)}</p>
                <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface-2/30">
                  <TxnField icon={Building2} label="من مكتب" value={t.created_by_name} />
                  {t.sender && <TxnField icon={UserRound} label="المرسِل" value={t.sender} />}
                  <TxnField icon={UserCheck} label="المستفيد" value={t.beneficiary} />
                  <TxnField icon={MapPin} label="الوجهة" value={t.destination} />
                  {t.currency_delivered !== t.currency_received && (
                    <TxnField icon={CalendarDays} label="التسليم بعملة" value={t.currency_delivered} />
                  )}
                  <TxnField icon={CalendarDays} label="الوقت"
                    value={<span className="tnum">{formatDateTime(t.created_at)}</span>} />
                </div>
                <Button onClick={() => openProcess(t)}>
                  <ClipboardCheck className="size-4" />معالجة
                </Button>
              </CardBody>
            </Card>
          ))}
        </div>
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>المرجع</TH><TH>الوقت</TH><TH>من مكتب</TH><TH>المرسِل</TH><TH>المستفيد</TH>
              <TH>المبلغ</TH><TH>التسليم</TH><TH>الوجهة</TH><TH>معالجة</TH>
            </TR>
          </THead>
          <TBody>
            {txns.map((t) => (
              <TR key={t.id}>
                <TD className="tnum text-sm text-muted">{t.reference_code}</TD>
                <TD className="tnum text-sm">{formatDateTime(t.created_at)}</TD>
                <TD>
                  {t.created_by_name}{" "}
                  <span className="tnum text-xs text-muted">({t.created_by_code})</span>
                </TD>
                <TD>{t.sender}</TD>
                <TD>{t.beneficiary}</TD>
                <TD className="tnum font-bold">{formatMoney(t.amount, t.currency_received)}</TD>
                <TD>
                  {t.currency_delivered !== t.currency_received ? (
                    <Badge status="pending">{t.currency_delivered} 💱</Badge>
                  ) : (
                    t.currency_delivered
                  )}
                </TD>
                <TD>{t.destination}</TD>
                <TD><Button size="sm" onClick={() => openProcess(t)}><ClipboardCheck className="size-4" />معالجة</Button></TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={processing !== null}
        onClose={() => setProcessing(null)}
        title={processing ? `معالجة ${processing.reference_code}` : ""}
      >
        {processing && (
          <div className="flex flex-col gap-4">
            <p className="rounded-md bg-surface-2 px-3 py-2 text-sm">
              {processing.sender} ← {processing.beneficiary} ·{" "}
              <span className="tnum font-bold">
                {formatMoney(processing.amount, processing.currency_received)}
              </span>{" "}
              → {processing.destination}
              {dual && ` · التسليم بـ${processing.currency_delivered}`}
            </p>
            <Select
              label="صندوق الوسيط (الذي ستُرسل منه الحركة)"
              placeholder="اختر الصندوق"
              options={eligibleBoxes.map((b) => ({ value: String(b.id), label: `${b.name} #${b.number}` }))}
              value={form.box}
              onChange={(e) => setForm({ ...form, box: e.target.value })}
              error={eligibleBoxes.length === 0 ? `لا صندوق يدعم عملة ${processing.currency_delivered} — أضف العملة لصندوق أولاً.` : undefined}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label={`رأس مال الأجور (${processing.currency_received})`} type="number" step="0.01" min={0} className="tnum"
                value={form.fee_cost}
                onChange={(e) => setForm({ ...form, fee_cost: e.target.value })} />
              <Input label={`الأجور المستحقة (${processing.currency_received})`} type="number" step="0.01" min={0} className="tnum"
                value={form.fee_charged}
                onChange={(e) => setForm({ ...form, fee_charged: e.target.value })} />
            </div>
            <p className="text-sm text-muted">الأجور دائماً بعملة المبلغ المقبوضة ({processing.currency_received}).</p>
            {dual && (
              <Input
                label={`سعر الصرف (1 ${processing.currency_received} = ? ${processing.currency_delivered})`}
                type="number" step="0.000001" min={0} className="tnum"
                value={form.exchange_rate}
                onChange={(e) => setForm({ ...form, exchange_rate: e.target.value })}
                error={!form.exchange_rate ? "إلزامي قبل القبول عند اختلاف العملتين" : undefined}
              />
            )}
            {form.fee_cost && form.fee_charged && (
              <p className="text-sm text-accent">
                ربحك من هذه الحركة = {formatMoney(Number(form.fee_charged) - Number(form.fee_cost))}{" "}
                {processing.currency_received}
              </p>
            )}
            {error && <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
            <div className="flex justify-end gap-3">
              <Button variant="danger" disabled={busy} onClick={() => act("reject")}><X className="size-4" />رفض</Button>
              <Button
                disabled={busy || !form.box || !form.fee_cost || !form.fee_charged || (!!dual && !form.exchange_rate)}
                onClick={() => act("approve")}
              >
                {busy ? "جارٍ…" : <><Check className="size-4" />قبول الحركة</>}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
