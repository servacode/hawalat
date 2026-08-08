"use client";

/**
 * ملف المكتب الصغير الفردي الكامل (ملاحظة 34): بياناته + تعديلها +
 * أرصدته ومطابقته (تثبيت/إرسال واتساب) + كشف حسابه بالعملة +
 * سجل مطابقاته مع PDF + الحدود + استعادة كلمة المرور + الحظر.
 */

import {
  ArrowRight, Ban, CalendarDays, CirclePause, CirclePlay, FileText, Flag, Gauge, KeyRound,
  Link2, LockOpen, Mail, MessageCircle, Pencil, Phone, Save, UserRound,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Badge, Button, Card, CardBody, CardHeader, EmptyState, Input, Modal,
  CardTitle, Pagination, PasswordInput, Select, Skeleton, TBody, TD, TH, THead, TR,
  Table, usePagination, type BadgeStatus,
} from "@/components/ui";
import { TxnField } from "@/components/transactions/TxnField";
import { authedApi, authedDownload } from "@/lib/authedApi";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";
import { buildReconciliationMessage, sendToWhatsApp, type ReconciliationRow } from "@/lib/whatsapp";

interface Member {
  id: number; name: string; username: string; office_code: string;
  phone: string; email: string; whatsapp_group_name: string;
  whatsapp_group_link: string; whatsapp_chat_id: string;
  is_blocked: boolean; is_suspended: boolean; date_joined: string;
}
interface CurrencyRow { code: string; name: string }
interface Recon { user: string; office_code: string; last_at: string | null; rows: ReconciliationRow[] }
interface HistoryRec {
  id: number; at: string; by: string;
  rows: { currency: string; balance: string }[];
}
interface StatementLine {
  id: number; kind: string; note: string; memo: string;
  debit: string; credit: string; at: string;
}

const KIND_LABEL: Record<string, string> = {
  transaction: "حوالة", deposit: "اعتماد", withdraw: "سحب",
  payment: "قبض", reversal: "ملغاة/عكس", adjustment: "تسوية", settlement: "تسوية",
};
const KIND_BADGE: Record<string, BadgeStatus> = {
  transaction: "accepted", deposit: "delivered", withdraw: "pending",
  payment: "paid", reversal: "reversed", adjustment: "delivered", settlement: "delivered",
};

export default function MemberProfilePage() {
  const params = useParams<{ id: string }>();
  const memberId = params.id;

  const [member, setMember] = useState<Member | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [currencies, setCurrencies] = useState<CurrencyRow[]>([]);
  // المطابقة (معاينة حيّة = الأرصدة الحالية)
  const [recon, setRecon] = useState<Recon | null>(null);
  const [reconSent, setReconSent] = useState(false);
  const [reconError, setReconError] = useState<string | null>(null);
  const [sendBusy, setSendBusy] = useState(false);
  // كشف الحساب
  const [stCurrency, setStCurrency] = useState("");
  const [stLines, setStLines] = useState<StatementLine[] | null>(null);
  const stPager = usePagination(stLines ?? [], 10);
  // سجل المطابقات
  const [history, setHistory] = useState<HistoryRec[] | null>(null);
  // النوافذ
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "", phone: "", email: "",
    whatsapp_group_name: "", whatsapp_group_link: "",
  });
  const [editError, setEditError] = useState<string | null>(null);
  const [limitOpen, setLimitOpen] = useState(false);
  const [limitForm, setLimitForm] = useState({ currency: "", negative_limit: "" });
  const [resetOpen, setResetOpen] = useState(false);
  const [resetPw, setResetPw] = useState("");
  const [resetDone, setResetDone] = useState(false);

  const load = useCallback(() => {
    authedApi<Member>(`/api/office/members/${memberId}/`)
      .then(setMember)
      .catch(() => setNotFound(true));
    authedApi<Recon>(`/api/office/members/${memberId}/reconciliation/`).then(setRecon).catch(() => {});
    authedApi<HistoryRec[]>(`/api/office/members/${memberId}/reconciliations/`).then(setHistory).catch(() => {});
    authedApi<{ results?: CurrencyRow[] } | CurrencyRow[]>("/api/office/currencies/")
      .then((d) => setCurrencies(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, [memberId]);
  useEffect(load, [load]);

  // كشف الحساب حسب العملة المختارة
  useEffect(() => {
    if (!stCurrency) return;
    setStLines(null);
    authedApi<{ lines: StatementLine[] }>(
      `/api/office/members/${memberId}/statement/?currency=${stCurrency}`,
    )
      .then((d) => setStLines(d.lines))
      .catch(() => setStLines([]));
  }, [memberId, stCurrency]);

  async function sendRecon() {
    if (!recon || !member || sendBusy) return;
    setReconError(null);
    setSendBusy(true);
    try {
      // كل إرسال مطابقة = نقطة إغلاق مرجعية تلقائياً (ملاحظة 50) — تثبيت ثم إرسال
      let committed: Recon;
      try {
        committed = await authedApi<Recon>(
          `/api/office/members/${memberId}/reconciliation/`,
          { method: "POST" },
        );
        setRecon(committed);
        authedApi<HistoryRec[]>(`/api/office/members/${memberId}/reconciliations/`).then(setHistory).catch(() => {});
      } catch {
        setReconError("تعذر تثبيت المطابقة — حاول مجدداً.");
        return;
      }
      const text = buildReconciliationMessage(committed.rows);
      try {
        // الرقم مربوط (ملاحظة 44)؟ تُرسل مباشرة من رقم المكتب بلا أي رابط
        const r = await authedApi<{ status: string; error: string }>(
          "/api/whatsapp/send/",
          { method: "POST", body: { text, member_id: member.id } },
        );
        if (r.status === "sent") {
          setReconSent(true);
          setTimeout(() => setReconSent(false), 4000);
        } else {
          // لم تُسلَّم فوراً — أظهر السبب الحقيقي بدل الصمت (ملاحظة 47)
          setReconError(r.error || "ثُبّتت — والرسالة لم تُرسل بعد، سيُعاد تلقائياً.");
        }
      } catch {
        // الوضع يدوي أو فشل → الرابط، مع إرشاد واضح مهما كانت النتيجة (ملاحظة 48)
        const how = await sendToWhatsApp(text, member.whatsapp_group_link || null);
        setReconError(
          how === "blocked"
            ? "ثُبّتت ✓ — لكن المتصفح منع النافذة: النص منسوخ، افتح المجموعة والصقه (Ctrl+V)."
            : how === "copied"
              ? "ثُبّتت ✓ — نُسخ النص وفُتحت المجموعة: الصقه (Ctrl+V) وأرسله."
              : "ثُبّتت ✓ — فُتحت نافذة مشاركة واتساب بالنص الجاهز.",
        );
      }
    } finally {
      setSendBusy(false);
    }
  }

  async function toggleSuspend() {
    if (!member) return;
    await authedApi(
      `/api/office/members/${member.id}/${member.is_suspended ? "unsuspend" : "suspend"}/`,
      { method: "POST" },
    );
    load();
  }

  async function toggleBlock() {
    if (!member) return;
    await authedApi(`/api/office/members/${member.id}/${member.is_blocked ? "unblock" : "block"}/`, { method: "POST" });
    load();
  }

  function openEdit() {
    if (!member) return;
    setEditError(null);
    setEditForm({
      name: member.name, phone: member.phone, email: member.email,
      whatsapp_group_name: member.whatsapp_group_name,
      whatsapp_group_link: member.whatsapp_group_link,
    });
    setEditOpen(true);
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    setEditError(null);
    try {
      await authedApi(`/api/office/members/${memberId}/`, { method: "PATCH", body: editForm });
      setEditOpen(false);
      load();
    } catch (err) {
      const data = (err as { data?: Record<string, string[] | string> })?.data;
      const first = data && Object.values(data)[0];
      setEditError((Array.isArray(first) ? first[0] : first) ?? "تعذر الحفظ — تأكد من البيانات.");
    }
  }

  async function saveLimit(e: React.FormEvent) {
    e.preventDefault();
    await authedApi("/api/office/credit-limits/", {
      method: "POST",
      body: { user: Number(memberId), ...limitForm },
    }).catch(() => {});
    setLimitOpen(false);
    setLimitForm({ currency: "", negative_limit: "" });
  }

  async function doReset(e: React.FormEvent) {
    e.preventDefault();
    await authedApi("/api/auth/reset-password/", {
      method: "POST",
      body: { user_id: Number(memberId), new_password: resetPw },
    });
    setResetDone(true);
    setTimeout(() => {
      setResetOpen(false);
      setResetPw("");
      setResetDone(false);
    }, 1200);
  }

  if (notFound) return <EmptyState title="المكتب غير موجود" action={<Link href="/office/members" className="text-brand-700 hover:underline">عودة إلى الحسابات</Link>} />;
  if (!member) return <Skeleton className="h-72" />;

  return (
    <div className="flex flex-col gap-4">
      {/* الرأس: عودة + الاسم + الحالة + الإجراءات */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/office/members"
            className="flex size-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            aria-label="عودة إلى الحسابات"
          >
            <ArrowRight className="size-5" />
          </Link>
          <div className="leading-tight">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              {member.name}
              {member.is_blocked ? (
                <Badge status="cancelled">محظور</Badge>
              ) : member.is_suspended ? (
                <Badge status="pending">موقوف مؤقتاً</Badge>
              ) : (
                <Badge status="accepted">نشط</Badge>
              )}
            </h2>
            <p dir="ltr" className="tnum text-xs text-muted">{member.office_code}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="accent" disabled={sendBusy} onClick={sendRecon}>
            <MessageCircle className="size-4" />
            {sendBusy ? "جارٍ الإرسال…" : "إرسال مطابقة"}
          </Button>
          <Button variant="ghost" onClick={openEdit}><Pencil className="size-4" />تعديل البيانات</Button>
          <Button variant="ghost" onClick={() => setLimitOpen(true)}><Gauge className="size-4" />الحدود</Button>
          <Button variant="ghost" onClick={() => setResetOpen(true)}><KeyRound className="size-4" />كلمة المرور</Button>
          <Button variant="ghost" onClick={toggleSuspend}
            title="الموقوف مؤقتاً يدخل حسابه لكن لا يرسل أي حركة">
            {member.is_suspended ? <><CirclePlay className="size-4" />تشغيل</> : <><CirclePause className="size-4" />إيقاف مؤقت</>}
          </Button>
          <Button variant={member.is_blocked ? "primary" : "danger"} onClick={toggleBlock}>
            {member.is_blocked ? <><LockOpen className="size-4" />فك الحظر</> : <><Ban className="size-4" />حظر</>}
          </Button>
        </div>
      </div>

      {/* نتيجة إرسال المطابقة — تحت الأزرار مباشرة */}
      {reconSent && <p className="text-sm text-success">أُرسلت عبر الواتساب ✓</p>}
      {reconError && <p className="text-sm text-danger">{reconError}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* بيانات المكتب */}
        <Card>
          <CardHeader><CardTitle>بيانات المكتب</CardTitle></CardHeader>
          <CardBody>
            <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface-2/30">
              <TxnField icon={UserRound} label="اسم المستخدم" value={member.username} />
              <TxnField icon={Phone} label="الهاتف" value={member.phone ? <span className="tnum">{member.phone}</span> : "—"} />
              <TxnField icon={Mail} label="البريد الإلكتروني" value={member.email || "—"} />
              <TxnField icon={MessageCircle} label="مجموعة الواتساب" value={member.whatsapp_group_name || "—"} />
              <TxnField icon={Link2} label="رابط المجموعة"
                value={member.whatsapp_group_link ? (
                  <a href={member.whatsapp_group_link} target="_blank" rel="noreferrer" dir="ltr"
                    className="text-brand-700 hover:underline">فتح الرابط</a>
                ) : "—"} />
              <TxnField icon={CalendarDays} label="تاريخ الفتح"
                value={<span className="tnum">{formatDate(member.date_joined)}</span>} />
            </div>
          </CardBody>
        </Card>

        {/* الأرصدة والمطابقة */}
        <Card>
          <CardHeader><CardTitle>الأرصدة والمطابقة</CardTitle></CardHeader>
          <CardBody className="flex flex-col gap-3">
            {!recon ? (
              <Skeleton className="h-32" />
            ) : (
              <>
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
                      <TR><TH>العملة</TH><TH>سابق</TH><TH>عليه</TH><TH>له</TH><TH>الصافي</TH></TR>
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
                <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
                  <Flag className="mb-0.5 inline size-4" /> كل «إرسال مطابقة» يثبّت هذه الأرصدة
                  نقطةَ إغلاق مرجعية تلقائياً ويرسلها للمكتب — وتجدها في السجل أدناه.
                </p>
              </>
            )}
          </CardBody>
        </Card>
      </div>

      {/* سجل المطابقات المثبّتة */}
      <Card>
        <CardHeader><CardTitle>سجل المطابقات المثبّتة</CardTitle></CardHeader>
        <CardBody className="flex flex-col gap-3">
          {!history ? (
            <Skeleton className="h-24" />
          ) : history.length === 0 ? (
            <p className="text-sm text-muted">لا مطابقات مثبّتة بعد — «إرسال مطابقة» أعلاه ينشئ أول سجل.</p>
          ) : (
            <Table>
              <THead>
                <TR><TH>التاريخ</TH><TH>ثبّتها</TH><TH>الأرصدة المثبّتة</TH><TH>ملف</TH></TR>
              </THead>
              <TBody>
                {history.map((r) => (
                  <TR key={r.id}>
                    <TD className="tnum text-sm">{formatDateTime(r.at)}</TD>
                    <TD>{r.by}</TD>
                    <TD className="tnum text-sm">
                      {r.rows.map((row) => `${row.currency} ${formatMoney(row.balance)}`).join(" · ") || "—"}
                    </TD>
                    <TD>
                      <Button size="sm" variant="ghost"
                        onClick={() => authedDownload(`/api/office/members/${memberId}/reconciliations/${r.id}/pdf/`, `مطابقة-${member.office_code}-${r.id}.pdf`)}>
                        <FileText className="size-4" />PDF
                      </Button>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardBody>
      </Card>

      {/* كشف الحساب بالعملة */}
      <Card>
        <CardHeader><CardTitle>كشف الحساب</CardTitle></CardHeader>
        <CardBody className="flex flex-col gap-3">
          <div className="max-w-64">
            <Select label="العملة" placeholder="اختر العملة"
              options={currencies.map((c) => ({ value: c.code, label: `${c.name} (${c.code})` }))}
              value={stCurrency}
              onChange={(e) => setStCurrency(e.target.value)} />
          </div>
          {!stCurrency ? (
            <p className="text-sm text-muted">اختر عملة لعرض حركات حساب المكتب فيها.</p>
          ) : !stLines ? (
            <Skeleton className="h-32" />
          ) : stLines.length === 0 ? (
            <EmptyState title="لا حركات بهذه العملة" />
          ) : (
            <>
              <Table>
                <THead>
                  <TR><TH>النوع</TH><TH>البيان</TH><TH>عليه</TH><TH>له</TH><TH>التاريخ</TH></TR>
                </THead>
                <TBody>
                  {stPager.slice.map((l) => (
                    <TR key={l.id}>
                      <TD><Badge status={KIND_BADGE[l.kind] ?? "delivered"}>{KIND_LABEL[l.kind] ?? "تسوية"}</Badge></TD>
                      <TD className="max-w-72 truncate">{l.note || l.memo || "—"}</TD>
                      <TD className="tnum text-neg">{Number(l.debit) ? formatMoney(l.debit) : "—"}</TD>
                      <TD className="tnum text-pos">{Number(l.credit) ? formatMoney(l.credit) : "—"}</TD>
                      <TD className="tnum text-sm">{formatDate(l.at)}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
              <Pagination page={stPager.page} pages={stPager.pages} total={stPager.total} onChange={stPager.setPage} />
            </>
          )}
        </CardBody>
      </Card>

      {/* تعديل البيانات */}
      <Modal open={editOpen} onClose={() => setEditOpen(false)} title={`تعديل بيانات ${member.name}`}>
        <form onSubmit={saveEdit} className="grid gap-4 sm:grid-cols-2">
          <Input label="اسم المكتب" value={editForm.name}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} required />
          <Input label="رقم هاتف واتساب" value={editForm.phone}
            onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
          <Input label="البريد الإلكتروني" type="email" dir="ltr" value={editForm.email}
            onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
          <Input label="اسم مجموعة الواتساب" value={editForm.whatsapp_group_name}
            onChange={(e) => setEditForm({ ...editForm, whatsapp_group_name: e.target.value })} />
          <Input label="رابط مجموعة الواتساب" dir="ltr" value={editForm.whatsapp_group_link}
            onChange={(e) => setEditForm({ ...editForm, whatsapp_group_link: e.target.value })} />
          {editError && <p className="text-sm text-danger sm:col-span-2">{editError}</p>}
          <div className="flex justify-end gap-3 sm:col-span-2">
            <Button type="button" variant="ghost" onClick={() => setEditOpen(false)}>إلغاء</Button>
            <Button type="submit"><Save className="size-4" />حفظ</Button>
          </div>
        </form>
      </Modal>

      {/* الحدود */}
      <Modal open={limitOpen} onClose={() => setLimitOpen(false)} title={`الحد السالب — ${member.name}`}>
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
            <Button type="button" variant="ghost" onClick={() => setLimitOpen(false)}>إلغاء</Button>
            <Button type="submit"><Save className="size-4" />حفظ الحد</Button>
          </div>
        </form>
      </Modal>

      {/* استعادة كلمة المرور */}
      <Modal open={resetOpen} onClose={() => setResetOpen(false)} title={`استعادة كلمة مرور ${member.name}`}>
        <form onSubmit={doReset} className="flex flex-col gap-4">
          <PasswordInput label="كلمة المرور الجديدة" hint="8 أحرف على الأقل"
            value={resetPw} onChange={(e) => setResetPw(e.target.value)} required minLength={8} />
          {resetDone && <p className="text-sm text-success">تمت الاستعادة ✓</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setResetOpen(false)}>إلغاء</Button>
            <Button type="submit"><KeyRound className="size-4" />إعادة التعيين</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
