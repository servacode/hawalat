"use client";

/**
 * شاشة التقارير الموحّدة (الجزء 20) — مكوّن مركزي واحد للدورين:
 * اختيار النوع + نطاق التاريخ + جدول عام + تنزيل Excel/PDF.
 */

import { useCallback, useEffect, useState } from "react";
import { Button, Card, CardBody, EmptyState, Input, Select, Skeleton, TBody, TD, TH, THead, TR, Table } from "@/components/ui";
import { authedApi, authedDownload } from "@/lib/authedApi";

interface ReportType { type: string; label: string }
interface Report { title: string; columns: string[]; rows: string[][] }

export function ReportsScreen({ scope }: { scope: "office" | "small" }) {
  const base = `/api/${scope}/reports/`;
  const [types, setTypes] = useState<ReportType[]>([]);
  const [type, setType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    authedApi<ReportType[]>(`${base}types/`).then((d) => {
      setTypes(d);
      if (d.length) setType(d[0].type);
    }).catch(() => {});
  }, [base]);

  const params = useCallback(() => {
    const p = new URLSearchParams({ type });
    if (dateFrom) p.set("date_from", dateFrom);
    if (dateTo) p.set("date_to", dateTo);
    return p;
  }, [type, dateFrom, dateTo]);

  const run = useCallback(() => {
    if (!type) return;
    setLoading(true);
    authedApi<Report>(`${base}?${params()}`)
      .then(setReport)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [base, type, params]);

  useEffect(run, [run]);

  async function download(fmt: "xlsx" | "pdf") {
    setDownloading(fmt);
    try {
      await authedDownload(`${base}?${params()}&export=${fmt}`, `hawalat-${type}.${fmt}`);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1">
            <Select label="التقرير" options={types.map((t) => ({ value: t.type, label: t.label }))}
              value={type} onChange={(e) => setType(e.target.value)} />
          </div>
          <Input label="من تاريخ" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="إلى تاريخ" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <Button variant="ghost" onClick={run}>عرض</Button>
          <Button variant="accent" disabled={downloading !== null} onClick={() => download("xlsx")}>
            {downloading === "xlsx" ? "جارٍ…" : "⬇ Excel"}
          </Button>
          <Button variant="accent" disabled={downloading !== null} onClick={() => download("pdf")}>
            {downloading === "pdf" ? "جارٍ…" : "⬇ PDF"}
          </Button>
        </CardBody>
      </Card>

      {loading || !report ? (
        <Skeleton className="h-64" />
      ) : report.rows.length === 0 ? (
        <EmptyState title={report.title} description="لا بيانات ضمن هذا النطاق." />
      ) : (
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-bold">{report.title}</h2>
          <Table>
            <THead>
              <TR>{report.columns.map((c) => <TH key={c}>{c}</TH>)}</TR>
            </THead>
            <TBody>
              {report.rows.map((row, i) => (
                <TR key={i}>
                  {row.map((v, j) => (
                    <TD key={j} className={/^-?[\d,.]+$/.test(v) ? "tnum" : ""}>{v}</TD>
                  ))}
                </TR>
              ))}
            </TBody>
          </Table>
        </div>
      )}
    </div>
  );
}
