"use client";

/** رئيسية المكتب الصغير: صناديقه لكل عملة (له/عليه/الصافي) + آخر الحركات. */

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, EmptyState, Skeleton, StatCard, TBody, TD, TH, THead, TR, Table, type BadgeStatus } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { onWsEvent } from "@/lib/ws";
import { balanceTone, formatMoney } from "@/lib/format";

interface BalanceRow {
  currency: string;
  owed_by_me: string;
  owed_to_me: string;
  net: string;
}
interface Txn {
  id: number;
  reference_code: string;
  beneficiary: string;
  amount: string;
  currency_received: string;
  destination: string;
  approval_status: "pending" | "accepted" | "cancelled" | "reversed";
}

const approvalBadge: Record<Txn["approval_status"], BadgeStatus> = {
  pending: "pending",
  accepted: "accepted",
  cancelled: "cancelled",
  reversed: "reversed",
};

export default function SmallHome() {
  const [balances, setBalances] = useState<BalanceRow[] | null>(null);
  const [txns, setTxns] = useState<Txn[] | null>(null);

  useEffect(() => {
    const load = () => {
      authedApi<{ balances: BalanceRow[] }>("/api/small/balances/")
        .then((d) => setBalances(d.balances))
        .catch(() => setBalances([]));
      authedApi<Txn[]>("/api/my/transactions/")
        .then((d) => setTxns(d.slice(0, 5)))
        .catch(() => setTxns([]));
    };
    load();
    return onWsEvent((e) => {
      if (e.kind === "refresh" || e.kind === "notification") load();
    });
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-bold uppercase tracking-widest text-brand-700">صناديقي</h2>
        {!balances ? (
          <Skeleton className="h-28" />
        ) : balances.length === 0 ? (
          <Card><CardBody className="text-muted">لا أرصدة بعد — سترى صناديقك هنا بعد أول حركة أو تسوية.</CardBody></Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {balances.map((b) => {
              const net = Number(b.net);
              return (
                <StatCard
                  key={b.currency}
                  title={`صندوق ${b.currency}`}
                  value={formatMoney(b.net)}
                  tone={balanceTone(net)}
                  detail={net > 0 ? "لك" : net < 0 ? "عليك" : "متوازن"}
                />
              );
            })}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-widest text-brand-700">آخر الحركات</h2>
          <Link href="/small/send"><Button size="sm">+ إرسال حركة</Button></Link>
        </div>
        {!txns ? (
          <Skeleton className="h-40" />
        ) : txns.length === 0 ? (
          <EmptyState title="لا حركات بعد" description="ابدأ بإرسال أول حوالة." action={<Link href="/small/send"><Button>إرسال حركة</Button></Link>} />
        ) : (
          <Table>
            <THead><TR><TH>المرجع</TH><TH>المستفيد</TH><TH>المبلغ</TH><TH>الوجهة</TH><TH>الحالة</TH></TR></THead>
            <TBody>
              {txns.map((t) => (
                <TR key={t.id}>
                  <TD className="tnum text-sm text-muted">{t.reference_code}</TD>
                  <TD>{t.beneficiary}</TD>
                  <TD className="tnum font-bold">{formatMoney(t.amount, t.currency_received)}</TD>
                  <TD>{t.destination}</TD>
                  <TD><Badge status={approvalBadge[t.approval_status]} /></TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </section>
    </div>
  );
}
