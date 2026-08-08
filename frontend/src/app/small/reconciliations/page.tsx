"use client";

/**
 * قسم المطابقات للمكتب الصغير (ملاحظة التجربة 12):
 * - مطابقة جديدة (معاينة → تثبيت وإرسال للواتساب إن سمح الكبير).
 * - سجل كل المطابقات المثبّتة بلقطتها الكاملة — مرجع دائم عند أي خلاف.
 */

import { ChevronDown, MessageCircle, Scale } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  EmptyState,
  Modal,
  Skeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  Table,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { authedApi } from "@/lib/authedApi";
import { getSession } from "@/lib/auth";
import { formatDateTime, formatMoney } from "@/lib/format";
import { buildReconciliationMessage, sendToWhatsApp, type ReconciliationRow } from "@/lib/whatsapp";

interface Recon {
  user: string;
  office_code: string;
  last_at: string | null;
  rows: ReconciliationRow[];
  allowed?: boolean;
}
interface HistoryRow {
  currency: string;
  previous?: string;
  debits?: string;
  credits?: string;
  balance: string;
}
interface HistoryRec {
  id: number;
  at: string;
  by: string;
  by_role: string;
  rows: HistoryRow[];
}

/** خلاصة الرصيد من منظور الصغير: القيمة المخزنة موجبة = عليه */
function netLabel(balance: string) {
  const b = Number(balance);
  if (b > 0) return { text: `${formatMoney(b)} عليك`, cls: "text-neg" };
  if (b < 0) return { text: `${formatMoney(-b)} لك`, cls: "text-pos" };
  return { text: "متوازن", cls: "" };
}

export default function SmallReconciliationsPage() {
  const [history, setHistory] = useState<HistoryRec[] | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  const [reconOpen, setReconOpen] = useState(false);
  const [recon, setRecon] = useState<Recon | null>(null);
  const [reconBusy, setReconBusy] = useState(false);
  const [waSent, setWaSent] = useState(false);

  const load = useCallback(() => {
    authedApi<HistoryRec[]>("/api/small/reconciliations/")
      .then(setHistory)
      .catch(() => setHistory([]));
  }, []);
  useEffect(load, [load]);

  async function openRecon() {
    setReconOpen(true);
    setRecon(null);
    setWaSent(false);
    const data = await authedApi<Recon>("/api/small/reconciliation/");
    setRecon(data);
  }

  async function commitAndSend() {
    setReconBusy(true);
    try {
      const data = await authedApi<Recon>("/api/small/reconciliation/", { method: "POST" });
      setRecon(data);
      const text = buildReconciliationMessage(data.user, data.office_code, data.rows, data.last_at);
      try {
        await authedApi("/api/whatsapp/send/", { method: "POST", body: { text } });
      } catch {
        const link = getSession()?.user.whatsapp_group_link;
        await sendToWhatsApp(text, link || null);
      }
      setWaSent(true);
      load();
    } finally {
      setReconBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">
          كل مطابقة نقطة إغلاق مثبّتة بلقطتها الكاملة — عند أي خطأ ارجع إليها لترى أين حصل.
        </p>
        <Button variant="accent" onClick={openRecon}>
          <Scale className="size-4" />
          مطابقة جديدة
        </Button>
      </div>

      {!history ? (
        <Skeleton className="h-48" />
      ) : history.length === 0 ? (
        <EmptyState
          title="لا مطابقات مثبّتة بعد"
          description="بعد أول تثبيت (منك بإذن مكتبك، أو من مكتبك) سيظهر سجل المطابقات هنا."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {history.map((r) => {
            const active = openId === r.id;
            return (
              <div key={r.id}>
                <button
                  type="button"
                  onClick={() => setOpenId(active ? null : r.id)}
                  aria-expanded={active}
                  className="w-full text-start focus-visible:outline-2 focus-visible:outline-brand"
                >
                  <Card
                    className={cn(
                      "transition-all hover:border-brand/50",
                      active && "border-brand ring-2 ring-brand/30",
                    )}
                  >
                    <CardBody className="flex flex-wrap items-center justify-between gap-3 py-3.5">
                      <div className="flex items-center gap-3">
                        <span className="flex size-9 items-center justify-center rounded-lg bg-brand/10 text-brand-700">
                          <Scale className="size-4.5" />
                        </span>
                        <div className="leading-tight">
                          <p className="tnum font-bold">{formatDateTime(r.at)}</p>
                          <p className="text-xs text-muted">
                            ثبّتها: {r.by} {r.by_role === "big_office" ? "(مكتبك)" : ""}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-3">
                        {r.rows.map((row) => {
                          const n = netLabel(row.balance);
                          return (
                            <span key={row.currency} className="tnum text-sm">
                              <span className="text-muted">{row.currency}:</span>{" "}
                              <span className={cn("font-bold", n.cls)}>{n.text}</span>
                            </span>
                          );
                        })}
                        <ChevronDown
                          className={cn("size-4 text-muted transition-transform", active && "rotate-180")}
                        />
                      </div>
                    </CardBody>
                  </Card>
                </button>

                {active && (
                  <Card className="mt-2 border-dashed">
                    <CardBody>
                      <Table>
                        <THead>
                          <TR>
                            <TH>العملة</TH>
                            <TH>الرصيد السابق</TH>
                            <TH>عليك (الفترة)</TH>
                            <TH>لك (الفترة)</TH>
                            <TH>الصافي المثبّت</TH>
                          </TR>
                        </THead>
                        <TBody>
                          {r.rows.map((row) => {
                            const n = netLabel(row.balance);
                            return (
                              <TR key={row.currency}>
                                <TD className="font-medium">{row.currency}</TD>
                                <TD className={cn("tnum", row.previous !== undefined && netLabel(row.previous).cls)}>
                                  {row.previous !== undefined ? netLabel(row.previous).text : "—"}
                                </TD>
                                <TD className="tnum">
                                  {row.debits !== undefined ? formatMoney(row.debits) : "—"}
                                </TD>
                                <TD className="tnum">
                                  {row.credits !== undefined ? formatMoney(row.credits) : "—"}
                                </TD>
                                <TD className={cn("tnum font-bold", n.cls)}>{n.text}</TD>
                              </TR>
                            );
                          })}
                        </TBody>
                      </Table>
                      <p className="mt-3 text-sm text-muted">
                        هذه لقطة لحظة التثبيت — لا تتغير أبداً. قارنها بكشف الصندوق لتحديد مكان أي فرق.
                      </p>
                    </CardBody>
                  </Card>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* مطابقة جديدة (معاينة → تثبيت إن سمح مكتبك) */}
      <Modal open={reconOpen} onClose={() => setReconOpen(false)} title="المطابقة مع مكتبك">
        {!recon ? (
          <Skeleton className="h-32" />
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted">
              {recon.last_at
                ? `منذ آخر مطابقة: ${formatDateTime(recon.last_at)}`
                : "أول مطابقة — تشمل كل الحركات"}
              {" · "}كشف دوري لا يُصفّر الحسابات.
            </p>
            <Table>
              <THead>
                <TR>
                  <TH>العملة</TH>
                  <TH>سابق</TH>
                  <TH>عليك</TH>
                  <TH>لك</TH>
                  <TH>الصافي</TH>
                </TR>
              </THead>
              <TBody>
                {recon.rows.map((r) => {
                  const bal = Number(r.balance);
                  return (
                    <TR key={r.currency}>
                      <TD className="font-medium">{r.currency}</TD>
                      <TD className="tnum">{formatMoney(r.previous)}</TD>
                      <TD className="tnum">{formatMoney(r.debits)}</TD>
                      <TD className="tnum">{formatMoney(r.credits)}</TD>
                      <TD className={`tnum font-bold ${bal > 0 ? "text-neg" : bal < 0 ? "text-pos" : ""}`}>
                        {formatMoney(Math.abs(bal))} {bal > 0 ? "عليك" : bal < 0 ? "لك" : ""}
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
            {waSent && <p className="text-sm text-success">ثُبّتت المطابقة وفُتح الواتساب بالنص ✓</p>}
            {recon.allowed ? (
              <div className="flex justify-end">
                <Button variant="accent" disabled={reconBusy} onClick={commitAndSend}>
                  {reconBusy ? "جارٍ…" : <><MessageCircle className="size-4" />تثبيت وإرسال للواتساب</>}
                </Button>
              </div>
            ) : (
              <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
                هذه معاينة فقط — تثبيت المطابقة وإرسالها معطّل من مكتبك.
                عند الحاجة لمطابقة رسمية اطلبها من مكتبك، أو يفعّل لك الصلاحية من إعداداته.
              </p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
