"use client";

/**
 * الصناديق (الأجزاء 7-ج، 9، 12 والمشهد 5):
 * تبويبان — صناديق الوسطاء (إضافة/اعتماد/سحب/كشف) وصندوق المحل (نقد لكل عملة + كشف).
 */

import { ChevronLeft, HandCoins, PackagePlus, Plus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, CardBody, EmptyState, Input, Modal, Select, Skeleton, Tabs } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { balanceTone, formatMoney } from "@/lib/format";

interface CurrencyRow { code: string; name: string }
interface Box {
  id: number; name: string; number: string; currencies: string[];
  balances: { currency: string; balance: string }[];
}

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
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", number: "", currencies: [] as string[] });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    authedApi<{ results?: Box[] } | Box[]>("/api/office/boxes/")
      .then((d) => setBoxes(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
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
            <Link key={b.id} href={`/office/boxes/${b.id}`}
              className="text-start focus-visible:outline-2 focus-visible:outline-brand">
              <Card className="transition-all hover:border-brand/50 hover:shadow-md">
                <CardBody className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <p className="font-bold">{b.name} <span className="tnum text-sm text-muted">#{b.number}</span></p>
                    <span className="flex items-center gap-1 text-xs text-muted">
                      التفاصيل والعمليات <ChevronLeft className="size-4" />
                    </span>
                  </div>
                  {b.balances.length === 0 ? (
                    <p className="text-sm text-muted">لا حركة بعد — العملات: {b.currencies.join("، ")}</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {b.balances.map((bal) => {
                        const tone = balanceTone(bal.balance);
                        return (
                          <span key={bal.currency}
                            className={`tnum rounded-md border border-border px-3 py-1.5 text-sm font-bold ${tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : ""}`}>
                            {bal.currency}: {formatMoney(bal.balance)}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </CardBody>
              </Card>
            </Link>
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

    </div>
  );
}

// ─────────────────────────────── صندوق المحل
function ShopCash() {
  const { currencies } = useCurrencies();
  const [balances, setBalances] = useState<{ currency: string; balance: string }[] | null>(null);
  const [members, setMembers] = useState<{ id: number; name: string }[]>([]);
  // دفعة نقدية من مكتب (ملاحظة 54)
  const [payOpen, setPayOpen] = useState(false);
  const [payForm, setPayForm] = useState({ member: "", currency: "", amount: "", memo: "" });
  const [payError, setPayError] = useState<string | null>(null);
  const [payDone, setPayDone] = useState(false);

  const load = useCallback(() => {
    authedApi<{ balances: { currency: string; balance: string }[] }>("/api/office/shop-cash/")
      .then((d) => setBalances(d.balances))
      .catch(() => setBalances([]));
  }, []);
  useEffect(load, [load]);
  useEffect(() => {
    authedApi<{ id: number; name: string }[]>("/api/office/members/").then(setMembers).catch(() => {});
  }, []);

  async function submitPayment(e: React.FormEvent) {
    e.preventDefault();
    setPayError(null);
    try {
      await authedApi("/api/office/shop-cash/payments/", {
        method: "POST",
        body: { ...payForm, member: Number(payForm.member) },
      });
      setPayDone(true);
      setTimeout(() => {
        setPayOpen(false);
        setPayDone(false);
        setPayForm({ member: "", currency: "", amount: "", memo: "" });
      }, 1200);
      load();
    } catch (err) {
      const data = (err as { data?: Record<string, string[] | string> })?.data;
      const first = data && Object.values(data)[0];
      setPayError((Array.isArray(first) ? first[0] : (first as string)) ?? "تعذر التسجيل — تأكد من البيانات.");
    }
  }

  if (!balances) return <Skeleton className="h-32" />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => { setPayOpen(true); setPayError(null); }}>
          <HandCoins className="size-4" />دفعة من مكتب
        </Button>
      </div>
      {balances.length === 0 ? (
        <EmptyState title="أضف عملات أولاً من قسم الصناديق" />
      ) : (
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
      )}

      {/* دفعة نقدية من مكتب (ملاحظة 54): تدخل القيد مع ملاحظة إلزامية */}
      <Modal open={payOpen} onClose={() => setPayOpen(false)} title="دفعة نقدية من مكتب">
        <form onSubmit={submitPayment} className="flex flex-col gap-4">
          <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
            المكتب الصغير جلب نقداً للمحل؟ سجّلها هنا — تدخل صندوق المحل وتُخصم مما عليه بقيد مسجّل.
          </p>
          <Select label="المكتب" placeholder="اختر المكتب"
            options={members.map((m) => ({ value: String(m.id), label: m.name }))}
            value={payForm.member}
            onChange={(e) => setPayForm({ ...payForm, member: e.target.value })} required />
          <div className="grid gap-4 sm:grid-cols-2">
            <Select label="العملة" placeholder="اختر العملة"
              options={currencies.map((c) => ({ value: c.code, label: `${c.name} (${c.code})` }))}
              value={payForm.currency}
              onChange={(e) => setPayForm({ ...payForm, currency: e.target.value })} required />
            <Input label="المبلغ" type="number" step="0.01" min={0} className="tnum"
              value={payForm.amount}
              onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} required />
          </div>
          <Input label="الملاحظة (إلزامية)" placeholder="مثال: دفعة نقدية بيد أبو أحمد"
            value={payForm.memo}
            onChange={(e) => setPayForm({ ...payForm, memo: e.target.value })} required />
          {payError && <p className="text-sm text-danger">{payError}</p>}
          {payDone && <p className="text-sm text-success">سُجّلت الدفعة ✓</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setPayOpen(false)}>إلغاء</Button>
            <Button type="submit" disabled={!payForm.memo.trim()}>
              <HandCoins className="size-4" />تسجيل الدفعة
            </Button>
          </div>
        </form>
      </Modal>
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
