"use client";

/**
 * صناديق المكتب الصغير (الجزء 3-د + المشهد 4):
 * صندوق لكل عملة (له/عليه/الصافي) + كشف تفصيلي + مطابقة تُرسل للواتساب بضغطة زر.
 */

import { useCallback, useEffect, useState } from "react";
import { Button, Card, CardBody, EmptyState, Modal, Skeleton, StatCard, TBody, TD, TH, THead, TR, Table } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { onWsEvent } from "@/lib/ws";
import { getSession } from "@/lib/auth";
import { balanceTone, formatDateTime, formatMoney } from "@/lib/format";
import { buildReconciliationMessage, sendToWhatsApp, type ReconciliationRow } from "@/lib/whatsapp";

interface BalanceRow { currency: string; owed_by_me: string; owed_to_me: string; net: string }
interface StatementLine { id: number; memo: string; debit: string; credit: string; at: string }
interface Recon { user: string; office_code: string; last_at: string | null; rows: ReconciliationRow[] }

export default function SmallBoxesPage() {
  const [balances, setBalances] = useState<BalanceRow[] | null>(null);
  const [stFor, setStFor] = useState<string | null>(null);
  const [stLines, setStLines] = useState<StatementLine[] | null>(null);
  const [stBalance, setStBalance] = useState("0");
  const [reconOpen, setReconOpen] = useState(false);
  const [recon, setRecon] = useState<Recon | null>(null);
  const [reconBusy, setReconBusy] = useState(false);
  const [waSent, setWaSent] = useState(false);

  const load = useCallback(() => {
    authedApi<{ balances: BalanceRow[] }>("/api/small/balances/")
      .then((d) => setBalances(d.balances))
      .catch(() => setBalances([]));
  }, []);
  useEffect(load, [load]);
  useEffect(
    () => onWsEvent((e) => {
      if (e.kind === "refresh" && e.scope === "balances") load();
    }),
    [load],
  );

  async function openStatement(currency: string) {
    setStFor(currency);
    setStLines(null);
    const data = await authedApi<{ balance: string; lines: StatementLine[] }>(
      `/api/small/statement/?currency=${currency}`,
    );
    setStBalance(data.balance);
    setStLines(data.lines);
  }

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
      const link = getSession()?.user.whatsapp_group_link;
      await sendToWhatsApp(
        buildReconciliationMessage(data.user, data.office_code, data.rows, data.last_at),
        link || null,
      );
      setWaSent(true);
    } finally {
      setReconBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <p className="text-muted">صندوق لكل عملة — الحساب تلقائي بالكامل.</p>
        <Button variant="accent" onClick={openRecon}>📊 مطابقة + إرسال</Button>
      </div>

      {!balances ? (
        <Skeleton className="h-32" />
      ) : balances.length === 0 ? (
        <EmptyState title="لا صناديق بعد" description="بعد أول حركة أو تسوية ستظهر صناديقك هنا." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {balances.map((b) => {
            const net = Number(b.net);
            return (
              <Card key={b.currency}>
                <CardBody className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <p className="font-bold">{b.currency}</p>
                    <Button size="sm" variant="ghost" onClick={() => openStatement(b.currency)}>الكشف</Button>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-xs text-muted">لك</p>
                      <p className="tnum font-bold text-pos">{formatMoney(b.owed_to_me)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted">عليك</p>
                      <p className="tnum font-bold text-neg">{formatMoney(b.owed_by_me)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted">الصافي</p>
                      <p className={`tnum font-bold ${balanceTone(net) === "pos" ? "text-pos" : balanceTone(net) === "neg" ? "text-neg" : ""}`}>
                        {formatMoney(b.net)}
                      </p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            );
          })}
        </div>
      )}

      {/* كشف عملة */}
      <Modal open={stFor !== null} onClose={() => setStFor(null)} title={stFor ? `كشف ${stFor}` : ""}>
        {!stLines ? (
          <Skeleton className="h-32" />
        ) : (
          <div className="flex flex-col gap-3">
            <StatCard
              title="الصافي (من منظورك)"
              value={formatMoney(-Number(stBalance))}
              tone={balanceTone(-Number(stBalance))}
              detail={-Number(stBalance) > 0 ? "لك" : -Number(stBalance) < 0 ? "عليك" : "متوازن"}
            />
            <Table>
              <THead><TR><TH>البيان</TH><TH>عليك</TH><TH>لك</TH><TH>الوقت</TH></TR></THead>
              <TBody>
                {stLines.map((l) => (
                  <TR key={l.id}>
                    <TD className="max-w-56 truncate">{l.memo}</TD>
                    <TD className="tnum text-neg">{Number(l.debit) ? formatMoney(l.debit) : "—"}</TD>
                    <TD className="tnum text-pos">{Number(l.credit) ? formatMoney(l.credit) : "—"}</TD>
                    <TD className="tnum text-sm">{formatDateTime(l.at)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
        )}
      </Modal>

      {/* المطابقة */}
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
              <THead><TR><TH>العملة</TH><TH>سابق</TH><TH>عليك</TH><TH>لك</TH><TH>الصافي</TH></TR></THead>
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
            <div className="flex justify-end">
              <Button variant="accent" disabled={reconBusy} onClick={commitAndSend}>
                {reconBusy ? "جارٍ…" : "📲 تثبيت وإرسال للواتساب"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
