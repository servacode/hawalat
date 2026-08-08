"use client";

/**
 * إرسال حركة (الجزء 3-أ + المشهد 2-أ):
 * مرسِل/مستفيد/مبلغ/عملة مقبوضة/عملة مسلَّمة/وجهة (يدوي) → حفظ →
 * زر واتساب يفتح مجموعة المكتب برابطها مع النص الجاهز.
 */

import { Bot, CircleCheck, MessageCircle, Plus, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Card, CardBody, CardHeader, CardTitle, Input, Select } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { getSession } from "@/lib/auth";
import { buildTransactionMessage, sendToWhatsApp } from "@/lib/whatsapp";

interface CurrencyRow { code: string; name: string }
interface BotStatus { bot_enabled: boolean; chat_configured: boolean }
interface CreatedTxn {
  reference_code: string; sender: string; beneficiary: string;
  amount: string; currency_received: string; currency_delivered: string;
  destination: string;
}

const empty = {
  sender: "", beneficiary: "", amount: "",
  currency_received: "", currency_delivered: "", destination: "",
};

export default function SendPage() {
  const [currencies, setCurrencies] = useState<CurrencyRow[]>([]);
  const [form, setForm] = useState(empty);
  const [created, setCreated] = useState<CreatedTxn | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [waState, setWaState] = useState<"copied" | "shared" | "bot" | null>(null);
  const [bot, setBot] = useState<BotStatus | null>(null);

  useEffect(() => {
    authedApi<BotStatus>("/api/whatsapp/status/").then(setBot).catch(() => {});
    // عملات المستأجر — نقطة الصغير للأرصدة لا تكفي؛ العملات تأتي من حركاته/إعداد الكبير.
    authedApi<{ results?: CurrencyRow[] } | CurrencyRow[]>("/api/small/currencies/")
      .then((d) => setCurrencies(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => setCurrencies([]));
  }, []);

  const options = currencies.map((c) => ({ value: c.code, label: `${c.name} (${c.code})` }));
  const dual = form.currency_received && form.currency_delivered &&
    form.currency_received !== form.currency_delivered;

  // اسم المرسِل اختياري — الباقي إجباري، والزر لا يتفعّل قبل اكتمالها
  const complete =
    form.beneficiary.trim() !== "" &&
    Number(form.amount) > 0 &&
    form.currency_received !== "" &&
    form.destination.trim() !== "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const txn = await authedApi<CreatedTxn>("/api/my/transactions/", {
        method: "POST",
        body: { ...form, currency_delivered: form.currency_delivered || form.currency_received },
      });
      setCreated(txn);
      setForm(empty);
    } catch {
      setError("تعذر إرسال الحركة — تأكد من البيانات والعملات.");
    } finally {
      setBusy(false);
    }
  }

  const botReady = !!bot?.bot_enabled && !!bot?.chat_configured;

  async function whatsapp() {
    if (!created) return;
    const text = buildTransactionMessage(created);
    if (botReady) {
      try {
        await authedApi("/api/whatsapp/send/", { method: "POST", body: { text } });
        setWaState("bot");
        return;
      } catch {
        /* فشل البوت → نتحول للرابط اليدوي */
      }
    }
    const link = getSession()?.user.whatsapp_group_link;
    const result = await sendToWhatsApp(text, link || null);
    setWaState(result);
  }

  if (created) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader><CardTitle className="flex items-center gap-2"><CircleCheck className="size-5 text-success" /> أُرسلت الحركة — قيد الانتظار</CardTitle></CardHeader>
        <CardBody className="flex flex-col gap-4">
          <p>
            الرقم المرجعي:{" "}
            <span className="tnum font-bold text-brand-700">{created.reference_code}</span>
          </p>
          <pre className="whitespace-pre-wrap rounded-md bg-surface-2 p-4 text-sm leading-7">
            {buildTransactionMessage(created)}
          </pre>
          {waState && (
            <p className="text-sm text-success">
              {waState === "bot"
                ? "أُرسلت تلقائياً لمجموعتك عبر البوت."
                : waState === "copied"
                  ? "نُسخ النص — الصقه في مجموعتك التي فُتحت الآن."
                  : "فُتحت نافذة الواتساب بالنص الجاهز."}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button variant="accent" onClick={whatsapp}>
              {botReady ? <><Bot className="size-4" />إرسال عبر البوت</> : <><MessageCircle className="size-4" />إرسال للواتساب</>}
            </Button>
            <Button variant="ghost" onClick={() => { setCreated(null); setWaState(null); }}>
              <Plus className="size-4" />حركة جديدة
            </Button>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-2xl">
      <CardHeader><CardTitle>إرسال حركة</CardTitle></CardHeader>
      <CardBody>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Input label="اسم المرسِل (اختياري)" value={form.sender}
            onChange={(e) => setForm({ ...form, sender: e.target.value })} />
          <Input label="اسم المستفيد" value={form.beneficiary}
            onChange={(e) => setForm({ ...form, beneficiary: e.target.value })} required />
          <Input label="المبلغ" type="number" step="0.01" min={0} className="tnum" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
          <Select label="العملة المقبوضة" placeholder="اختر العملة" options={options}
            value={form.currency_received}
            onChange={(e) => setForm({ ...form, currency_received: e.target.value })} required />
          <Select label="العملة المسلَّمة (اختياري — إن اختلفت)" placeholder="نفس العملة المقبوضة"
            options={options} value={form.currency_delivered}
            onChange={(e) => setForm({ ...form, currency_delivered: e.target.value })} />
          <Input label="الوجهة" hint="تُكتب يدوياً" value={form.destination}
            onChange={(e) => setForm({ ...form, destination: e.target.value })} required />
          {dual && (
            <p className="rounded-md bg-warning/10 px-3 py-2 text-sm text-warning sm:col-span-2">
              {`عملتان مختلفتان — سيُدخل مكتب ${getSession()?.user.tenant_name ?? ""} سعر الصرف قبل القبول.`}
            </p>
          )}
          <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted sm:col-span-2">
            {`ملاحظة: بعد الإرسال لا يمكنك تعديل الحركة — أي تصحيح يتم عبر مكتب ${getSession()?.user.tenant_name ?? ""}.`}
          </p>
          {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
          <div className="sm:col-span-2">
            <Button type="submit" size="lg" disabled={busy || !complete} className="w-full">
              {busy ? "جارٍ الإرسال…" : <><Send className="size-4" />إرسال الحركة</>}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  );
}
