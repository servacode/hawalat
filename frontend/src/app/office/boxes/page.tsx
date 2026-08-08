"use client";

/**
 * الصناديق (الأجزاء 7-ج، 9، 12 والمشهد 5):
 * تبويبان — صناديق الوسطاء (إضافة/اعتماد/سحب/كشف) وصندوق المحل (نقد لكل عملة + كشف).
 */

import { ArrowDownToLine, ArrowUpFromLine, PackagePlus, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, CardBody, EmptyState, Input, Modal, Select, Skeleton, TBody, TD, TH, THead, TR, Table, Tabs } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { balanceTone, formatDateTime, formatMoney } from "@/lib/format";

interface CurrencyRow { code: string; name: string }
interface Box {
  id: number; name: string; number: string; currencies: string[];
  balances: { currency: string; balance: string }[];
}
interface Member { id: number; name: string; office_code: string }
interface StatementLine { id: number; memo: string; debit: string; credit: string; at: string }

function useCurrencies() {
  const [currencies, setCurrencies] = useState<CurrencyRow[]>([]);
  const load = useCallback(() => {
    authedApi<{ results?: CurrencyRow[] } | CurrencyRow[]>("/api/office/currencies/")
      .then((d) => setCurrencies(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);
  return { currencies, reload: load };
}

// ─────────────────────────────── صناديق الوسطاء
function IntermediaryBoxes() {
  const { currencies } = useCurrencies();
  const [boxes, setBoxes] = useState<Box[] | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", number: "", currencies: [] as string[] });
  const [settleFor, setSettleFor] = useState<{ box: Box; kind: "deposit" | "withdraw" } | null>(null);
  const [settleForm, setSettleForm] = useState({ small_user: "", currency: "", amount: "" });
  const [statementFor, setStatementFor] = useState<Box | null>(null);
  const [stCurrency, setStCurrency] = useState("");
  const [stLines, setStLines] = useState<StatementLine[] | null>(null);
  const [stBalance, setStBalance] = useState<string>("0");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    authedApi<{ results?: Box[] } | Box[]>("/api/office/boxes/")
      .then((d) => setBoxes(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
    authedApi<Member[]>("/api/office/members/").then(setMembers).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function addBox(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await authedApi("/api/office/boxes/", { method: "POST", body: addForm });
      setAddOpen(false);
      setAddForm({ name: "", number: "", currencies: [] });
      load();
    } catch {
      setError("تعذر الإضافة — تأكد من رقم صندوق غير مكرر وعملة واحدة على الأقل.");
    }
  }

  async function settle(e: React.FormEvent) {
    e.preventDefault();
    if (!settleFor) return;
    setError(null);
    try {
      await authedApi(`/api/office/boxes/${settleFor.box.id}/${settleFor.kind}/`, {
        method: "POST", body: settleForm,
      });
      setSettleFor(null);
      setSettleForm({ small_user: "", currency: "", amount: "" });
      load();
    } catch (err) {
      const detail = (err as { data?: { detail?: string } })?.data?.detail;
      setError(detail ?? "تعذرت العملية.");
    }
  }

  async function openStatement(box: Box, currency: string) {
    setStatementFor(box);
    setStCurrency(currency);
    setStLines(null);
    const data = await authedApi<{ balance: string; lines: StatementLine[] }>(
      `/api/office/boxes/${box.id}/statement/?currency=${currency}`,
    );
    setStBalance(data.balance);
    setStLines(data.lines);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setAddOpen(true)}><PackagePlus className="size-4" />صندوق وسيط</Button>
      </div>
      {!boxes ? (
        <Skeleton className="h-48" />
      ) : boxes.length === 0 ? (
        <EmptyState title="لا صناديق وسطاء بعد"
          description="أضف صندوقاً (اسم + رقم + عملات) لتمرير الحركات من خلاله."
          action={<Button onClick={() => setAddOpen(true)}><PackagePlus className="size-4" />إضافة صندوق</Button>} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {boxes.map((b) => (
            <Card key={b.id}>
              <CardBody className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <p className="font-bold">{b.name} <span className="tnum text-sm text-muted">#{b.number}</span></p>
                  <div className="flex gap-1.5">
                    <Button size="sm" variant="ghost" onClick={() => setSettleFor({ box: b, kind: "deposit" })}><ArrowDownToLine className="size-4" />اعتماد</Button>
                    <Button size="sm" variant="ghost" onClick={() => setSettleFor({ box: b, kind: "withdraw" })}><ArrowUpFromLine className="size-4" />سحب</Button>
                  </div>
                </div>
                {b.balances.length === 0 ? (
                  <p className="text-sm text-muted">لا حركة بعد — العملات: {b.currencies.join("، ")}</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {b.balances.map((bal) => {
                      const tone = balanceTone(bal.balance);
                      return (
                        <button key={bal.currency}
                          onClick={() => openStatement(b, bal.currency)}
                          className={`tnum rounded-md border border-border px-3 py-1.5 text-sm font-bold transition-colors hover:border-brand ${tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : ""}`}>
                          {bal.currency}: {formatMoney(bal.balance)}
                        </button>
                      );
                    })}
                  </div>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="إضافة صندوق وسيط (اسم + رقم + عملات)">
        <form onSubmit={addBox} className="flex flex-col gap-4">
          <Input label="اسم الصندوق" placeholder="الوعد" value={addForm.name}
            onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} required />
          <Input label="رقم الصندوق" placeholder="101" value={addForm.number}
            onChange={(e) => setAddForm({ ...addForm, number: e.target.value })} required />
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">العملات المتاحة فيه</span>
            <div className="flex flex-wrap gap-2">
              {currencies.map((c) => {
                const active = addForm.currencies.includes(c.code);
                return (
                  <button type="button" key={c.code}
                    onClick={() => setAddForm({
                      ...addForm,
                      currencies: active
                        ? addForm.currencies.filter((x) => x !== c.code)
                        : [...addForm.currencies, c.code],
                    })}
                    className={`rounded-full border px-3 py-1 text-sm transition-colors ${active ? "border-brand bg-brand/10 font-bold text-brand-700" : "border-border text-muted hover:border-brand"}`}>
                    {c.code}
                  </button>
                );
              })}
            </div>
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setAddOpen(false)}>إلغاء</Button>
            <Button type="submit" disabled={addForm.currencies.length === 0}><PackagePlus className="size-4" />إضافة</Button>
          </div>
        </form>
      </Modal>

      <Modal open={settleFor !== null} onClose={() => setSettleFor(null)}
        title={settleFor ? `${settleFor.kind === "deposit" ? "اعتماد في" : "سحب من"} ${settleFor.box.name}` : ""}>
        {settleFor && (
          <form onSubmit={settle} className="flex flex-col gap-4">
            <p className="text-sm text-muted">
              {settleFor.kind === "deposit"
                ? "الاعتماد يُسجَّل باسم مكتب صغير: يزيد الصندوق ويُنقص ما عليه (تعزيز رصيد)."
                : "السحب: ينقص الصندوق ويزيد ما على المكتب الصغير."}
            </p>
            <Select label="باسم المكتب الصغير" placeholder="اختر المكتب"
              options={members.map((m) => ({ value: String(m.id), label: `${m.name} (${m.office_code})` }))}
              value={settleForm.small_user}
              onChange={(e) => setSettleForm({ ...settleForm, small_user: e.target.value })} required />
            <Select label="العملة" placeholder="اختر العملة"
              options={settleFor.box.currencies.map((c) => ({ value: c, label: c }))}
              value={settleForm.currency}
              onChange={(e) => setSettleForm({ ...settleForm, currency: e.target.value })} required />
            <Input label="المبلغ" type="number" step="0.01" min={0} className="tnum" value={settleForm.amount}
              onChange={(e) => setSettleForm({ ...settleForm, amount: e.target.value })} required />
            {error && <p className="text-sm text-danger">{error}</p>}
            <div className="flex justify-end gap-3">
              <Button type="button" variant="ghost" onClick={() => setSettleFor(null)}>إلغاء</Button>
              <Button type="submit">{settleFor.kind === "deposit" ? <><ArrowDownToLine className="size-4" />تنفيذ الاعتماد</> : <><ArrowUpFromLine className="size-4" />تنفيذ السحب</>}</Button>
            </div>
          </form>
        )}
      </Modal>

      <Modal open={statementFor !== null} onClose={() => setStatementFor(null)}
        title={statementFor ? `كشف ${statementFor.name} — ${stCurrency}` : ""}>
        {!stLines ? (
          <Skeleton className="h-32" />
        ) : (
          <div className="flex flex-col gap-3">
            <p className="tnum font-bold">
              الرصيد الجاري: <span className={Number(stBalance) >= 0 ? "text-pos" : "text-neg"}>{formatMoney(stBalance, stCurrency)}</span>
            </p>
            <Table>
              <THead><TR><TH>البيان</TH><TH>مدين</TH><TH>دائن</TH><TH>الوقت</TH></TR></THead>
              <TBody>
                {stLines.map((l) => (
                  <TR key={l.id}>
                    <TD className="max-w-56 truncate">{l.memo}</TD>
                    <TD className="tnum">{Number(l.debit) ? formatMoney(l.debit) : "—"}</TD>
                    <TD className="tnum">{Number(l.credit) ? formatMoney(l.credit) : "—"}</TD>
                    <TD className="tnum text-sm">{formatDateTime(l.at)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ─────────────────────────────── صندوق المحل
function ShopCash() {
  const [balances, setBalances] = useState<{ currency: string; balance: string }[] | null>(null);

  useEffect(() => {
    authedApi<{ balances: { currency: string; balance: string }[] }>("/api/office/shop-cash/")
      .then((d) => setBalances(d.balances))
      .catch(() => setBalances([]));
  }, []);

  if (!balances) return <Skeleton className="h-32" />;
  if (balances.length === 0) return <EmptyState title="أضف عملات أولاً من قسم الصناديق" />;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {balances.map((b) => (
        <Card key={b.currency}>
          <CardBody>
            <p className="text-sm text-muted">نقد {b.currency}</p>
            <p className={`tnum mt-1 text-2xl font-bold ${Number(b.balance) > 0 ? "text-pos" : ""}`}>
              {formatMoney(b.balance)}
            </p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

// ─────────────────────────────── إدارة العملات
function CurrenciesManager() {
  const { currencies, reload } = useCurrencies();
  const [form, setForm] = useState({ code: "", name: "" });

  async function add(e: React.FormEvent) {
    e.preventDefault();
    await authedApi("/api/office/currencies/", { method: "POST", body: form }).catch(() => {});
    setForm({ code: "", name: "" });
    reload();
  }

  return (
    <div className="flex max-w-xl flex-col gap-4">
      <form onSubmit={add} className="flex items-end gap-3">
        <Input label="الرمز" placeholder="USD" dir="ltr" value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} required />
        <div className="flex-1">
          <Input label="الاسم" placeholder="دولار أمريكي" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>
        <Button type="submit"><Plus className="size-4" />إضافة</Button>
      </form>
      <div className="flex flex-wrap gap-2">
        {currencies.map((c) => (
          <span key={c.code} className="rounded-full border border-border bg-surface px-3 py-1 text-sm">
            {c.name} <b className="tnum">({c.code})</b>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function BoxesPage() {
  return (
    <Tabs
      tabs={[
        { key: "boxes", label: "صناديق الوسطاء", content: <IntermediaryBoxes /> },
        { key: "shop", label: "صندوق المحل (النقد)", content: <ShopCash /> },
        { key: "currencies", label: "العملات", content: <CurrenciesManager /> },
      ]}
    />
  );
}
