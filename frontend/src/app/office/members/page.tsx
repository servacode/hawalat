"use client";

/**
 * قسم الحسابات (الجزء 10): فتح/تعديل/حظر المكاتب الصغيرة + ملف كل عضو
 * (واتساب/هاتف/كود) + حدوده + كشفه + مطابقته (المشهد 4) بإرسال واتساب.
 */

import { Ban, Flag, Gauge, KeyRound, LockOpen, MessageCircle, Save, Scale, UserPlus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, EmptyState, Input, Modal, PasswordInput, Select, Skeleton, TBody, TD, TH, THead, TR, Table } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime, formatMoney } from "@/lib/format";
import { buildReconciliationMessage, sendToWhatsApp, type ReconciliationRow } from "@/lib/whatsapp";

interface Member {
  id: number; name: string; username: string; office_code: string;
  phone: string; whatsapp_group_name: string; whatsapp_group_link: string;
  is_blocked: boolean;
}
interface CurrencyRow { code: string; name: string }
interface Recon { user: string; office_code: string; last_at: string | null; rows: ReconciliationRow[] }

const emptyCreate = {
  name: "", username: "", password: "", phone: "",
  whatsapp_group_name: "", whatsapp_group_link: "", whatsapp_chat_id: "",
};

export default function MembersPage() {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [currencies, setCurrencies] = useState<CurrencyRow[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(emptyCreate);
  const [error, setError] = useState<string | null>(null);
  // المطابقة
  const [reconFor, setReconFor] = useState<Member | null>(null);
  const [recon, setRecon] = useState<Recon | null>(null);
  const [reconBusy, setReconBusy] = useState(false);
  // الحدود
  const [limitFor, setLimitFor] = useState<Member | null>(null);
  const [limitForm, setLimitForm] = useState({ currency: "", negative_limit: "" });
  // استعادة كلمة المرور
  const [resetFor, setResetFor] = useState<Member | null>(null);
  const [resetPw, setResetPw] = useState("");
  const [resetDone, setResetDone] = useState(false);

  const load = useCallback(() => {
    authedApi<Member[]>("/api/office/members/").then(setMembers).catch(() => {});
    authedApi<{ results?: CurrencyRow[] } | CurrencyRow[]>("/api/office/currencies/")
      .then((d) => setCurrencies(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function createMember(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await authedApi("/api/office/members/", { method: "POST", body: createForm });
      setCreateOpen(false);
      setCreateForm(emptyCreate);
      load();
    } catch (err) {
      const detail = (err as { data?: { detail?: string } })?.data?.detail;
      setError(detail ?? "تعذر الإنشاء — تأكد من البيانات.");
    }
  }

  async function toggleBlock(m: Member) {
    await authedApi(`/api/office/members/${m.id}/${m.is_blocked ? "unblock" : "block"}/`, { method: "POST" });
    load();
  }

  async function openRecon(m: Member) {
    setReconFor(m);
    setRecon(null);
    const data = await authedApi<Recon>(`/api/office/members/${m.id}/reconciliation/`);
    setRecon(data);
  }

  async function commitRecon() {
    if (!reconFor) return;
    setReconBusy(true);
    try {
      const data = await authedApi<Recon>(`/api/office/members/${reconFor.id}/reconciliation/`, { method: "POST" });
      setRecon(data);
    } finally {
      setReconBusy(false);
    }
  }

  async function sendRecon() {
    if (!recon || !reconFor) return;
    const text = buildReconciliationMessage(recon.user, recon.office_code, recon.rows, recon.last_at);
    // بوت أولاً (إن كان مفعّلاً) ثم الرابط اليدوي
    try {
      await authedApi("/api/whatsapp/send/", {
        method: "POST",
        body: { text, member_id: reconFor.id },
      });
      return;
    } catch {
      /* الوضع يدوي أو فشل → الرابط */
    }
    await sendToWhatsApp(text, reconFor.whatsapp_group_link || null);
  }

  async function doReset(e: React.FormEvent) {
    e.preventDefault();
    if (!resetFor) return;
    await authedApi("/api/auth/reset-password/", {
      method: "POST",
      body: { user_id: resetFor.id, new_password: resetPw },
    });
    setResetDone(true);
    setTimeout(() => {
      setResetFor(null);
      setResetPw("");
      setResetDone(false);
    }, 1200);
  }

  async function saveLimit(e: React.FormEvent) {
    e.preventDefault();
    if (!limitFor) return;
    await authedApi("/api/office/credit-limits/", {
      method: "POST",
      body: { user: limitFor.id, ...limitForm },
    }).catch(() => {});
    setLimitFor(null);
    setLimitForm({ currency: "", negative_limit: "" });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-muted">مكاتبك الصغيرة — الفتح ضمن حد الباقة، وكل ملف يجمع كل ما يخص العضو.</p>
        <Button onClick={() => setCreateOpen(true)}><UserPlus className="size-4" />مكتب صغير جديد</Button>
      </div>

      {!members ? (
        <Skeleton className="h-64" />
      ) : members.length === 0 ? (
        <EmptyState title="لا مكاتب صغيرة بعد" action={<Button onClick={() => setCreateOpen(true)}><UserPlus className="size-4" />فتح أول مكتب</Button>} />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>الكود</TH><TH>الاسم</TH><TH>المستخدم</TH><TH>الهاتف</TH>
              <TH>مجموعة الواتساب</TH><TH>الحالة</TH><TH>إجراءات</TH>
            </TR>
          </THead>
          <TBody>
            {members.map((m) => (
              <TR key={m.id}>
                <TD className="tnum text-sm text-muted">{m.office_code}</TD>
                <TD className="font-medium">{m.name}</TD>
                <TD>{m.username}</TD>
                <TD className="tnum">{m.phone || "—"}</TD>
                <TD>{m.whatsapp_group_name || "—"}</TD>
                <TD>
                  {m.is_blocked ? <Badge status="cancelled">محظور</Badge> : <Badge status="accepted">نشط</Badge>}
                </TD>
                <TD>
                  <div className="flex flex-wrap gap-1.5">
                    <Button size="sm" variant="ghost" onClick={() => openRecon(m)}><Scale className="size-4" />مطابقة</Button>
                    <Button size="sm" variant="ghost" onClick={() => setLimitFor(m)}><Gauge className="size-4" />الحدود</Button>
                    <Button size="sm" variant="ghost" onClick={() => setResetFor(m)} aria-label="استعادة كلمة المرور"><KeyRound className="size-4" /></Button>
                    <Button size="sm" variant={m.is_blocked ? "primary" : "danger"} onClick={() => toggleBlock(m)}>
                      {m.is_blocked ? <><LockOpen className="size-4" />فك الحظر</> : <><Ban className="size-4" />حظر</>}
                    </Button>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {/* إنشاء عضو */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="فتح مكتب صغير جديد">
        <form onSubmit={createMember} className="grid gap-4 sm:grid-cols-2">
          <Input label="اسم المكتب" value={createForm.name}
            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} required />
          <Input label="اسم المستخدم" value={createForm.username}
            onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })} required />
          <PasswordInput label="كلمة المرور" hint="8 أحرف على الأقل" value={createForm.password}
            onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} required />
          <Input label="رقم هاتف واتساب" value={createForm.phone}
            onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })} />
          <Input label="اسم مجموعة الواتساب" value={createForm.whatsapp_group_name}
            onChange={(e) => setCreateForm({ ...createForm, whatsapp_group_name: e.target.value })} />
          <Input label="رابط مجموعة الواتساب" dir="ltr" placeholder="https://chat.whatsapp.com/…"
            value={createForm.whatsapp_group_link}
            onChange={(e) => setCreateForm({ ...createForm, whatsapp_group_link: e.target.value })} />
          <Input label="معرّف مجموعة البوت (اختياري)" dir="ltr" placeholder="12036…@g.us"
            hint="يلزم فقط عند تفعيل وضع البوت"
            value={createForm.whatsapp_chat_id}
            onChange={(e) => setCreateForm({ ...createForm, whatsapp_chat_id: e.target.value })} />
          {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
          <div className="flex justify-end gap-3 sm:col-span-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>إلغاء</Button>
            <Button type="submit"><UserPlus className="size-4" />فتح المكتب</Button>
          </div>
        </form>
      </Modal>

      {/* المطابقة */}
      <Modal open={reconFor !== null} onClose={() => setReconFor(null)}
        title={reconFor ? `مطابقة ${reconFor.name}` : ""}>
        {!recon ? (
          <Skeleton className="h-32" />
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted">
              {recon.last_at
                ? `منذ آخر مطابقة: ${formatDateTime(recon.last_at)} — رصيد سابق + حركات الفترة فقط`
                : "أول مطابقة — تشمل كل الحركات"}
            </p>
            {recon.rows.length === 0 ? (
              <p className="text-muted">لا حسابات/حركات بعد.</p>
            ) : (
              <Table>
                <THead>
                  <TR><TH>العملة</TH><TH>سابق</TH><TH>عليكم</TH><TH>لكم</TH><TH>الصافي</TH></TR>
                </THead>
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
                          {formatMoney(r.balance)} {bal > 0 ? "(عليه)" : bal < 0 ? "(له)" : ""}
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>
            )}
            <div className="flex flex-wrap justify-end gap-3">
              <Button variant="accent" onClick={sendRecon}><MessageCircle className="size-4" />إرسال مطابقة</Button>
              <Button disabled={reconBusy} onClick={commitRecon}>
                {reconBusy ? "جارٍ…" : <><Flag className="size-4" />تثبيت كنقطة إغلاق</>}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* استعادة كلمة المرور (الجزء 10) */}
      <Modal open={resetFor !== null} onClose={() => setResetFor(null)}
        title={resetFor ? `استعادة كلمة مرور ${resetFor.name}` : ""}>
        <form onSubmit={doReset} className="flex flex-col gap-4">
          <PasswordInput label="كلمة المرور الجديدة" hint="8 أحرف على الأقل"
            value={resetPw} onChange={(e) => setResetPw(e.target.value)} required minLength={8} />
          {resetDone && <p className="text-sm text-success">تمت الاستعادة ✓</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setResetFor(null)}>إلغاء</Button>
            <Button type="submit"><KeyRound className="size-4" />إعادة التعيين</Button>
          </div>
        </form>
      </Modal>

      {/* الحدود */}
      <Modal open={limitFor !== null} onClose={() => setLimitFor(null)}
        title={limitFor ? `الحد السالب — ${limitFor.name}` : ""}>
        <form onSubmit={saveLimit} className="flex flex-col gap-4">
          <Select label="العملة" placeholder="اختر العملة"
            options={currencies.map((c) => ({ value: c.code, label: `${c.name} (${c.code})` }))}
            value={limitForm.currency}
            onChange={(e) => setLimitForm({ ...limitForm, currency: e.target.value })} required />
          <Input label="الحد السالب المسموح" type="number" step="0.01" min={0} className="tnum"
            hint="مثال: 5000 تعني يُسمح له بالإرسال حتى يبلغ عليه 5000"
            value={limitForm.negative_limit}
            onChange={(e) => setLimitForm({ ...limitForm, negative_limit: e.target.value })} required />
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setLimitFor(null)}>إلغاء</Button>
            <Button type="submit"><Save className="size-4" />حفظ الحد</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
