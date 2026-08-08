"use client";

/**
 * شاشة التقارير الاحترافية (ملاحظة 55) — مكوّن مركزي واحد للدورين:
 * بطاقات تقارير مصنّفة (بدل القائمة المنسدلة) + فترات جاهزة/مخصصة +
 * جدول نتائج بباجينيشن + تنزيل Excel/PDF للتقرير المعروض بنطاقه.
 */

import {
  Activity, ArrowLeftRight, Banknote, BarChart3, Building2, CalendarCheck,
  FileSpreadsheet, FileText, ListChecks, MapPin, Package, Scale, TrendingUp,
  Trophy, Wallet, type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  Button, Card, CardBody, EmptyState, Input, Pagination, Skeleton,
  TBody, TD, TH, THead, TR, Table, usePagination,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { authedApi, authedDownload } from "@/lib/authedApi";

interface ReportType { type: string; label: string }
interface Report { title: string; columns: string[]; rows: string[][] }

/** هوية كل تقرير: أيقونة + وصف موجز + فئة — والافتراضي للأنواع الجديدة. */
const REPORT_META: Record<string, { icon: LucideIcon; desc: string; cat: string }> = {
  summary: { icon: Wallet, desc: "لك وعليك والصافي لكل عملة", cat: "المال والأرباح" },
  profits: { icon: TrendingUp, desc: "أرباح فرق الأجور بكل عملة", cat: "المال والأرباح" },
  profits_by_member: { icon: BarChart3, desc: "من أين تأتي الأرباح؟ مكتباً بمكتب", cat: "المال والأرباح" },
  shop_cash: { icon: Banknote, desc: "داخل وخارج نقد المحل", cat: "المال والأرباح" },
  activity: { icon: Activity, desc: "عدد الحركات وحجمها بالفترة", cat: "النشاط والحركات" },
  by_status: { icon: ListChecks, desc: "توزيع الحركات على الحالات", cat: "النشاط والحركات" },
  by_destination: { icon: MapPin, desc: "أين تتجه الحوالات؟", cat: "النشاط والحركات" },
  top_members: { icon: Trophy, desc: "المكاتب الأكثر نشاطاً", cat: "النشاط والحركات" },
  daily_close: { icon: CalendarCheck, desc: "كشف إقفال اليوم", cat: "النشاط والحركات" },
  member_summary: { icon: Building2, desc: "أرصدة المكاتب الصغيرة وحركتها", cat: "الأطراف والتسويات" },
  box_summary: { icon: Package, desc: "أرصدة صناديق الوسطاء", cat: "الأطراف والتسويات" },
  settlements: { icon: Scale, desc: "الاعتمادات والسحوبات والتسويات", cat: "الأطراف والتسويات" },
  exchange_rates: { icon: ArrowLeftRight, desc: "أسعار الصرف الفعلية من الحركات", cat: "الأطراف والتسويات" },
};
const DEFAULT_META = { icon: FileText, desc: "", cat: "تقارير أخرى" };
const CAT_ORDER = ["المال والأرباح", "النشاط والحركات", "الأطراف والتسويات", "تقارير أخرى"];

const PRESETS = [
  { key: "today", label: "اليوم" },
  { key: "7d", label: "آخر 7 أيام" },
  { key: "month", label: "هذا الشهر" },
  { key: "all", label: "منذ البداية" },
] as const;

function isoDay(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function ReportsScreen({ scope }: { scope: "office" | "small" }) {
  const base = `/api/${scope}/reports/`;
  const [types, setTypes] = useState<ReportType[]>([]);
  const [type, setType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [preset, setPreset] = useState<string>("all");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const pager = usePagination(report?.rows ?? [], 12);

  useEffect(() => {
    authedApi<ReportType[]>(`${base}types/`).then((d) => {
      setTypes(d);
      if (d.length) setType(d[0].type);
    }).catch(() => {});
  }, [base]);

  function applyPreset(key: string) {
    setPreset(key);
    const now = new Date();
    if (key === "today") {
      setDateFrom(isoDay(now));
      setDateTo(isoDay(now));
    } else if (key === "7d") {
      const from = new Date(now);
      from.setDate(now.getDate() - 6);
      setDateFrom(isoDay(from));
      setDateTo(isoDay(now));
    } else if (key === "month") {
      setDateFrom(isoDay(new Date(now.getFullYear(), now.getMonth(), 1)));
      setDateTo(isoDay(now));
    } else {
      setDateFrom("");
      setDateTo("");
    }
  }

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

  // تجميع البطاقات بالفئات وفق ترتيب ثابت
  const grouped = CAT_ORDER.map((cat) => ({
    cat,
    items: types.filter((t) => (REPORT_META[t.type] ?? DEFAULT_META).cat === cat),
  })).filter((g) => g.items.length > 0);

  const activeLabel = types.find((t) => t.type === type)?.label ?? "";

  return (
    <div className="flex flex-col gap-5">
      {/* بطاقات التقارير المصنّفة — الضغط يختار ويعرض */}
      {types.length === 0 ? (
        <Skeleton className="h-40" />
      ) : (
        grouped.map((g) => (
          <div key={g.cat} className="flex flex-col gap-2.5">
            <h2 className="text-sm font-bold text-muted">{g.cat}</h2>
            <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
              {g.items.map((t) => {
                const meta = REPORT_META[t.type] ?? DEFAULT_META;
                const Icon = meta.icon;
                const active = t.type === type;
                return (
                  <button key={t.type} type="button" onClick={() => setType(t.type)}
                    aria-pressed={active}
                    className={cn(
                      "flex items-start gap-3 rounded-xl border p-3 text-start transition-all focus-visible:outline-2 focus-visible:outline-brand",
                      active
                        ? "border-brand bg-brand/5 shadow-sm"
                        : "border-border bg-surface hover:border-brand/50",
                    )}>
                    <span className={cn(
                      "flex size-9 shrink-0 items-center justify-center rounded-lg",
                      active ? "bg-brand text-white" : "bg-surface-2 text-brand",
                    )}>
                      <Icon className="size-4.5" />
                    </span>
                    <span className="min-w-0">
                      <span className={cn("block text-sm font-bold", active && "text-brand-700")}>
                        {t.label}
                      </span>
                      {meta.desc && <span className="block text-xs text-muted">{meta.desc}</span>}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))
      )}

      {/* شريط الفترة والتنزيل للتقرير المختار */}
      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {PRESETS.map((p) => (
              <button key={p.key} type="button" onClick={() => applyPreset(p.key)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-sm transition-colors",
                  preset === p.key
                    ? "border-brand bg-brand text-white"
                    : "border-border text-muted hover:border-brand/50 hover:text-ink",
                )}>
                {p.label}
              </button>
            ))}
          </div>
          <Input label="من تاريخ" type="date" value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPreset(""); }} />
          <Input label="إلى تاريخ" type="date" value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPreset(""); }} />
          <div className="ms-auto flex gap-2">
            <Button variant="accent" disabled={downloading !== null} onClick={() => download("xlsx")}>
              {downloading === "xlsx" ? "جارٍ…" : (<><FileSpreadsheet className="size-4" /> Excel</>)}
            </Button>
            <Button variant="accent" disabled={downloading !== null} onClick={() => download("pdf")}>
              {downloading === "pdf" ? "جارٍ…" : (<><FileText className="size-4" /> PDF</>)}
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* النتيجة */}
      {loading || !report ? (
        <Skeleton className="h-64" />
      ) : report.rows.length === 0 ? (
        <EmptyState title={activeLabel || report.title} description="لا بيانات ضمن هذا النطاق." />
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-bold">{report.title}</h2>
            <p className="tnum text-sm text-muted">{report.rows.length} سطراً</p>
          </div>
          <Table>
            <THead>
              <TR>{report.columns.map((c) => <TH key={c}>{c}</TH>)}</TR>
            </THead>
            <TBody>
              {pager.slice.map((row, i) => (
                <TR key={i}>
                  {row.map((v, j) => (
                    <TD key={j} className={/^-?[\d,.]+$/.test(v) ? "tnum" : ""}>{v}</TD>
                  ))}
                </TR>
              ))}
            </TBody>
          </Table>
          <Pagination page={pager.page} pages={pager.pages} total={pager.total} onChange={pager.setPage} />
        </div>
      )}
    </div>
  );
}
