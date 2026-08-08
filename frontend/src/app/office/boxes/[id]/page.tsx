"use client";

/**
 * صفحة تفاصيل صندوق الوسيط (ملاحظة التجربة 16):
 * كل حركات الصندوق (اعتماد/سحب/تسوية/حركات) بعملة محددة + فلاتر
 * (النوع/المكتب/التاريخ) + مجاميع «لنا/له» + أزرار اعتماد/سحب/تسوية بسبب إلزامي.
 */

import {
  ArrowDownToLine,
  ArrowUpFromLine,
  ArrowRight,
  Scale,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Input,
  Modal,
  Select,
  Skeleton,
  StatCard,
  TBody,
  TD,
  TH,
  THead,
  TR,
  Table,
  ViewToggle,
  useViewMode,
  type BadgeStatus,
} from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { balanceTone, formatDateTime, formatMoney } from "@/lib/format";

interface Box {
  id: number;
  name: string;
  number: string;
  currencies: string[];
}
interface Member {
  id: number;
  name: string;
  office_code: string;
}
interface MovementRow {
  id: number;
  at: string;
  memo: string;
  kind: "deposit" | "withdraw" | "adjustment" | "transaction" | "reversal" | "settlement";
  member: string;
  in: string;
  out: string;
}
interface Movements {
  currency: string;
  balance: string;
  totals: { in: string; out: string };
  rows: MovementRow[];
}

const KIND_LABEL: Record<MovementRow["kind"], string> = {
  deposit: "اعتماد",
  withdraw: "سحب",
  adjustment: "تسوية",
  transaction: "حركة",
  reversal: "عكس",
  settlement: "تسوية",
};
const KIND_BADGE: Record<MovementRow["kind"], BadgeStatus> = {
  deposit: "accepted",
  withdraw: "pending",
  adjustment: "delivered",
  transaction: "paid",
  reversal: "reversed",
  settlement: "delivered",
};

export default function BoxDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [box, setBox] = useState<Box | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [currency, setCurrency] = useState("");
  const [data, setData] = useState<Movements | null>(null);
  const [view, setView] = useViewMode();

  // الفلاتر (ملاحظة 16): النوع + المكتب + التاريخ
  const [kind, setKind] = useState("");
  const [member, setMember] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // نافذة العمليات (اعتماد/سحب/تسوية) — السبب إلزامي في الثلاثة
  const [op, setOp] = useState<"deposit" | "withdraw" | "adjust" | null>(null);
  const [opForm, setOpForm] = useState({
    small_user: "",
    amount: "",
    direction: "in",
    reason: "",
  });
  const [opError, setOpError] = useState<string | null>(null);
  const [opBusy, setOpBusy] = useState(false);

  useEffect(() => {
    authedApi<Box>(`/api/office/boxes/${id}/`).then((b) => {
      setBox(b);
      setCurrency((c) => c || b.currencies[0] || "");
    }).catch(() => {});
    authedApi<Member[]>("/api/office/members/").then(setMembers).catch(() => {});
  }, [id]);

  const load = useCallback(() => {
    if (!currency) return;
    const params = new URLSearchParams({ currency });
    if (kind) params.set("kind", kind);
    if (member) params.set("member", member);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    authedApi<Movements>(`/api/office/boxes/${id}/movements/?${params}`)
      .then(setData)
      .catch(() => {});
  }, [id, currency, kind, member, dateFrom, dateTo]);
  useEffect(load, [load]);

  async function submitOp(e: React.FormEvent) {
    e.preventDefault();
    setOpError(null);
    setOpBusy(true);
    try {
      if (op === "adjust") {
        await authedApi(`/api/office/boxes/${id}/adjust/`, {
          method: "POST",
          body: {
            currency,
            amount: opForm.amount,
            direction: opForm.direction,
            reason: opForm.reason,
          },
        });
      } else {
        await authedApi(`/api/office/boxes/${id}/${op}/`, {
          method: "POST",
          body: {
            small_user: opForm.small_user,
            currency,
            amount: opForm.amount,
            memo: opForm.reason,
          },
        });
      }
      setOp(null);
      setOpForm({ small_user: "", amount: "", direction: "in", reason: "" });
      load();
    } catch (err) {
      const d = (err as { data?: { detail?: string; memo?: string[] } })?.data;
      setOpError(d?.detail ?? d?.memo?.[0] ?? "تعذر التنفيذ — تأكد من البيانات والسبب.");
    } finally {
      setOpBusy(false);
    }
  }

  if (!box) return <Skeleton className="h-72" />;

  const balance = Number(data?.balance ?? 0);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/office/boxes"
            className="flex size-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            aria-label="عودة للصناديق"
          >
            <ArrowRight className="size-5" />
          </Link>
          <div className="leading-tight">
            <h2 className="text-lg font-bold">{box.name}</h2>
            <p dir="ltr" className="tnum text-xs text-muted">#{box.number}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={() => { setOp("deposit"); setOpError(null); }}>
            <ArrowDownToLine className="size-4" />اعتماد
          </Button>
          <Button variant="ghost" onClick={() => { setOp("withdraw"); setOpError(null); }}>
            <ArrowUpFromLine className="size-4" />سحب
          </Button>
          <Button variant="accent" onClick={() => { setOp("adjust"); setOpError(null); }}>
            <Scale className="size-4" />تسوية
          </Button>
        </div>
      </div>

      {box.currencies.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {box.currencies.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCurrency(c)}
              aria-pressed={c === currency}
              className={
                c === currency
                  ? "rounded-full bg-brand px-4 py-1.5 text-sm font-semibold text-white"
                  : "rounded-full border border-border bg-surface px-4 py-1.5 text-sm text-muted transition-colors hover:border-brand/50 hover:text-ink"
              }
            >
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          title="رصيدنا في الصندوق"
          value={formatMoney(Math.abs(balance))}
          tone={balanceTone(balance)}
          detail={balance > 0 ? "لنا" : balance < 0 ? "له علينا" : "متوازن"}
        />
        <StatCard title="داخل (مجموع الفترة)" value={formatMoney(data?.totals.in ?? 0)} tone="pos" />
        <StatCard title="خارج (مجموع الفترة)" value={formatMoney(data?.totals.out ?? 0)} tone="neg" />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-36">
          <Select label="النوع" placeholder="الكل" value={kind} onChange={(e) => setKind(e.target.value)}
            options={[
              { value: "deposit", label: "اعتماد" },
              { value: "withdraw", label: "سحب" },
              { value: "adjustment", label: "تسوية" },
              { value: "transaction", label: "حركات" },
              { value: "reversal", label: "عكس" },
            ]} />
        </div>
        <div className="min-w-44">
          <Select label="المكتب" placeholder="الكل" value={member} onChange={(e) => setMember(e.target.value)}
            options={members.map((m) => ({ value: String(m.id), label: m.name }))} />
        </div>
        <Input label="من تاريخ" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <Input label="إلى تاريخ" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <ViewToggle mode={view} onChange={setView} />
      </div>

      {!data ? (
        <Skeleton className="h-64" />
      ) : data.rows.length === 0 ? (
        <EmptyState title="لا حركات بهذه الفلاتر" />
      ) : view === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.rows.map((r) => (
            <Card key={r.id}>
              <CardBody className="flex flex-col gap-2 py-3.5">
                <div className="flex items-center justify-between gap-2">
                  <Badge status={KIND_BADGE[r.kind]}>{KIND_LABEL[r.kind]}</Badge>
                  <span className="tnum text-xs text-muted">{formatDateTime(r.at)}</span>
                </div>
                <p className="tnum text-lg font-bold">
                  {Number(r.in) > 0 ? (
                    <span className="text-pos">+{formatMoney(r.in)}</span>
                  ) : (
                    <span className="text-neg">−{formatMoney(r.out)}</span>
                  )}
                </p>
                {r.member && <p className="text-sm"><span className="text-muted">المكتب:</span> {r.member}</p>}
                <p className="break-words text-sm text-muted">{r.memo}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>الوقت</TH><TH>النوع</TH><TH>المكتب</TH><TH>البيان</TH>
              <TH>داخل (لنا)</TH><TH>خارج</TH>
            </TR>
          </THead>
          <TBody>
            {data.rows.map((r) => (
              <TR key={r.id}>
                <TD className="tnum text-sm">{formatDateTime(r.at)}</TD>
                <TD><Badge status={KIND_BADGE[r.kind]}>{KIND_LABEL[r.kind]}</Badge></TD>
                <TD>{r.member || "—"}</TD>
                <TD className="max-w-72">{r.memo}</TD>
                <TD className="tnum text-pos">{Number(r.in) ? formatMoney(r.in) : "—"}</TD>
                <TD className="tnum text-neg">{Number(r.out) ? formatMoney(r.out) : "—"}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {/* اعتماد / سحب / تسوية — السبب إلزامي دائماً */}
      <Modal
        open={op !== null}
        onClose={() => setOp(null)}
        title={
          op === "deposit"
            ? `اعتماد في ${box.name} — ${currency}`
            : op === "withdraw"
              ? `سحب من ${box.name} — ${currency}`
              : `تسوية ${box.name} — ${currency}`
        }
      >
        <form onSubmit={submitOp} className="flex flex-col gap-4">
          {op === "adjust" ? (
            <>
              <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
                التسوية لتصحيح رصيد سابق أو فرق جرد — لا تخص مكتباً صغيراً، وتُقيَّد على حساب «تسويات الصناديق».
              </p>
              <Select label="الاتجاه" value={opForm.direction}
                onChange={(e) => setOpForm({ ...opForm, direction: e.target.value })}
                options={[
                  { value: "in", label: "إضافة لرصيدنا في الصندوق" },
                  { value: "out", label: "خصم من رصيدنا في الصندوق" },
                ]} />
            </>
          ) : (
            <Select label="المكتب الصغير" placeholder="اختر المكتب" required value={opForm.small_user}
              onChange={(e) => setOpForm({ ...opForm, small_user: e.target.value })}
              options={members.map((m) => ({ value: String(m.id), label: `${m.name} (${m.office_code})` }))} />
          )}
          <Input label="المبلغ" type="number" step="0.01" min={0} className="tnum" required
            value={opForm.amount} onChange={(e) => setOpForm({ ...opForm, amount: e.target.value })} />
          <Input
            label="السبب"
            required
            placeholder={op === "deposit" ? "مثال: تعزيز رصيد نقدي مستلم بالمحل" : op === "withdraw" ? "مثال: إعادة مبلغ فائض للمكتب" : "مثال: رصيد افتتاحي سابق قبل اعتماد النظام"}
            hint="سبب واضح إلزامي — يظهر في الكشف وسجل التدقيق"
            value={opForm.reason}
            onChange={(e) => setOpForm({ ...opForm, reason: e.target.value })}
          />
          {opError && <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{opError}</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setOp(null)}>إلغاء</Button>
            <Button type="submit" disabled={opBusy || !opForm.reason.trim() || !opForm.amount || (op !== "adjust" && !opForm.small_user)}>
              {op === "deposit" ? <><ArrowDownToLine className="size-4" />تنفيذ الاعتماد</>
                : op === "withdraw" ? <><ArrowUpFromLine className="size-4" />تنفيذ السحب</>
                : <><Scale className="size-4" />تنفيذ التسوية</>}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
