"use client";

/**
 * صناديق المكتب الصغير (الجزء 3-د + المشهد 4):
 * صندوق لكل عملة (له/عليه/الصافي) + كشف تفصيلي + مطابقة تُرسل للواتساب بضغطة زر.
 */

import { ChevronDown, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, EmptyState, Skeleton, StatCard, TBody, TD, TH, THead, TR, Table, type BadgeStatus } from "@/components/ui";
import { cn } from "@/lib/cn";
import { authedApi } from "@/lib/authedApi";
import { onWsEvent } from "@/lib/ws";
import { balanceTone, formatDate, formatMoney } from "@/lib/format";

interface BalanceRow { currency: string; owed_by_me: string; owed_to_me: string; net: string }
interface StatementLine {
  id: number; memo: string; kind: string; note: string;
  debit: string; credit: string; at: string;
}

// تصنيف أنواع الكشف (ملاحظة 22): نوع واضح بدل البيان الخام
const KIND_LABEL: Record<string, string> = {
  transaction: "حوالة", deposit: "اعتماد", withdraw: "سحب",
  payment: "قبض", reversal: "ملغاة/عكس", adjustment: "تسوية", settlement: "تسوية",
};
const KIND_BADGE: Record<string, BadgeStatus> = {
  transaction: "accepted", deposit: "delivered", withdraw: "pending",
  payment: "paid", reversal: "reversed", adjustment: "delivered", settlement: "delivered",
};

export default function SmallBoxesPage() {
  const [balances, setBalances] = useState<BalanceRow[] | null>(null);
  const [stFor, setStFor] = useState<string | null>(null);
  const [stLines, setStLines] = useState<StatementLine[] | null>(null);
  const [stBalance, setStBalance] = useState("0");

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

  // الكرت الذكي: ضغطة تفتح الكشف التفصيلي بالأسفل، وضغطة ثانية تغلقه
  async function toggleStatement(currency: string) {
    if (stFor === currency) {
      setStFor(null);
      return;
    }
    setStFor(currency);
    setStLines(null);
    const data = await authedApi<{ balance: string; lines: StatementLine[] }>(
      `/api/small/statement/?currency=${currency}`,
    );
    setStBalance(data.balance);
    setStLines(data.lines);
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-muted">
        صندوق لكل عملة — الحساب تلقائي بالكامل. للمطابقة الرسمية وسجلها: قسم «المطابقات».
      </p>

      {!balances ? (
        <Skeleton className="h-32" />
      ) : balances.length === 0 ? (
        <EmptyState title="لا صناديق بعد" description="بعد أول حركة أو تسوية ستظهر صناديقك هنا." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {balances.map((b) => {
            const net = Number(b.net);
            const active = stFor === b.currency;
            return (
              <button
                key={b.currency}
                type="button"
                onClick={() => toggleStatement(b.currency)}
                aria-expanded={active}
                className="text-start focus-visible:outline-2 focus-visible:outline-brand"
              >
                <Card
                  className={cn(
                    "transition-all",
                    // الدلالة اللونية (ملاحظة 14): أحمر = مطلوب منك، أخضر = لك
                    net < 0 && "border-danger/60 bg-danger/10",
                    net > 0 && "border-success/60 bg-success/10",
                    net === 0 && "hover:border-brand/50",
                    active && "ring-2 ring-brand/40",
                  )}
                >
                  <CardBody className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <p className="font-bold">{b.currency}</p>
                      <span className="flex items-center gap-1 text-xs text-muted">
                        التفاصيل
                        <ChevronDown className={cn("size-4 transition-transform", active && "rotate-180")} />
                      </span>
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
              </button>
            );
          })}
        </div>
      )}

      {/* الكشف التفصيلي — يظهر أسفل الكروت عند الضغط على كرت العملة */}
      {stFor && (
        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>كشف {stFor} التفصيلي — لنا ولكم</CardTitle>
            <Button size="sm" variant="ghost" onClick={() => setStFor(null)} aria-label="إغلاق الكشف">
              <X className="size-4" />
            </Button>
          </CardHeader>
          <CardBody>
            {!stLines ? (
              <Skeleton className="h-40" />
            ) : (
              (() => {
                const net = -Number(stBalance);
                const totalOurs = stLines.reduce((s, l) => s + Number(l.credit), 0);
                const totalYours = stLines.reduce((s, l) => s + Number(l.debit), 0);
                return (
                  <div className="flex flex-col gap-4">
                    <div className="grid gap-3 sm:grid-cols-3">
                      <StatCard title="لنا (مجموع)" value={formatMoney(totalOurs)} tone="pos" />
                      <StatCard title="لكم (مجموع)" value={formatMoney(totalYours)} tone="neg" />
                      <StatCard
                        title="الصافي"
                        value={formatMoney(net)}
                        tone={balanceTone(net)}
                        detail={net > 0 ? "لنا" : net < 0 ? "لكم" : "متوازن"}
                      />
                    </div>
                    {stLines.length === 0 ? (
                      <EmptyState title="لا حركات بهذه العملة بعد" />
                    ) : (
                      <Table>
                        <THead><TR><TH>النوع</TH><TH>البيان</TH><TH>لنا</TH><TH>لكم</TH><TH>التاريخ</TH></TR></THead>
                        <TBody>
                          {stLines.map((l) => (
                            <TR key={l.id}>
                              <TD>
                                <Badge status={KIND_BADGE[l.kind] ?? "delivered"}>
                                  {KIND_LABEL[l.kind] ?? "تسوية"}
                                </Badge>
                              </TD>
                              <TD className="max-w-64">
                                <span dir="auto" className="tnum">{l.note || l.memo}</span>
                              </TD>
                              <TD className="tnum text-pos">{Number(l.credit) ? formatMoney(l.credit) : "—"}</TD>
                              <TD className="tnum text-neg">{Number(l.debit) ? formatMoney(l.debit) : "—"}</TD>
                              <TD className="tnum text-sm">{formatDate(l.at)}</TD>
                            </TR>
                          ))}
                        </TBody>
                      </Table>
                    )}
                  </div>
                );
              })()
            )}
          </CardBody>
        </Card>
      )}

    </div>
  );
}
