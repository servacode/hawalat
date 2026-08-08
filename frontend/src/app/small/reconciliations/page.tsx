"use client";

/**
 * قسم المطابقات للمكتب الصغير (ملاحظتا التجربة 12 و14):
 * مشاهدة فقط — سجل كل المطابقات التي ثبّتها مكتبه بلقطتها الكاملة + تنزيل PDF.
 * لا زر مطابقة هنا: التثبيت من المكتب الكبير حصراً.
 */

import { ChevronDown, FileText, Scale } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  EmptyState,
  Skeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  Table,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { authedApi, authedDownload } from "@/lib/authedApi";
import { formatDateTime, formatMoney } from "@/lib/format";

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


  const load = useCallback(() => {
    authedApi<HistoryRec[]>("/api/small/reconciliations/")
      .then(setHistory)
      .catch(() => setHistory([]));
  }, []);
  useEffect(load, [load]);

  return (
    <div className="flex flex-col gap-5">
      <p className="text-muted">
        كل مطابقة يثبّتها مكتبك تُحفظ هنا بلقطتها الكاملة — عند أي خطأ ارجع إليها لترى أين حصل،
        ويمكنك تنزيل أي مطابقة ملف PDF.
      </p>

      {!history ? (
        <Skeleton className="h-48" />
      ) : history.length === 0 ? (
        <EmptyState
          title="لا مطابقات مثبّتة بعد"
          description="بعد أول مطابقة يثبّتها مكتبك سيظهر سجلها هنا."
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
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm text-muted">
                          هذه لقطة لحظة التثبيت — لا تتغير أبداً. قارنها بكشف الصندوق لتحديد مكان أي فرق.
                        </p>
                        <Button
                          size="sm"
                          variant="accent"
                          onClick={() =>
                            authedDownload(
                              `/api/small/reconciliations/${r.id}/pdf/`,
                              `مطابقة-${r.id}.pdf`,
                            )
                          }
                        >
                          <FileText className="size-4" /> تنزيل PDF
                        </Button>
                      </div>
                    </CardBody>
                  </Card>
                )}
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
