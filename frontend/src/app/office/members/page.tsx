"use client";

/**
 * قسم الحسابات: قائمة المكاتب الصغيرة (جدول/كروت) + فتح مكتب جديد.
 * الضغط على المكتب يفتح ملفه الفردي الكامل (ملاحظة 34) — كل الإجراءات هناك.
 */

import { Mail, MessageCircle, Phone, UserPlus, UserRound } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Badge, Button, Card, CardBody, EmptyState, Input, Modal, Pagination,
  PasswordInput, Skeleton, TBody, TD, TH, THead, TR, Table, ViewToggle,
  usePagination, useViewMode,
} from "@/components/ui";
import { TxnField } from "@/components/transactions/TxnField";
import { authedApi } from "@/lib/authedApi";

interface Member {
  id: number; name: string; username: string; office_code: string;
  phone: string; email: string; whatsapp_group_name: string;
  is_blocked: boolean; is_suspended: boolean;
}

const emptyCreate = {
  name: "", username: "", password: "", phone: "", email: "",
  whatsapp_group_name: "", whatsapp_group_link: "",
};

export default function MembersPage() {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(emptyCreate);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useViewMode();
  const pager = usePagination(members ?? [], 9);

  const load = useCallback(() => {
    authedApi<Member[]>("/api/office/members/").then(setMembers).catch(() => {});
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">مكاتبك الصغيرة — اضغط على المكتب لفتح ملفه الكامل.</p>
        <div className="flex items-center gap-2">
          <ViewToggle mode={view} onChange={setView} />
          <Button onClick={() => setCreateOpen(true)}><UserPlus className="size-4" />مكتب صغير جديد</Button>
        </div>
      </div>

      {!members ? (
        <Skeleton className="h-64" />
      ) : members.length === 0 ? (
        <EmptyState title="لا مكاتب صغيرة بعد" action={<Button onClick={() => setCreateOpen(true)}><UserPlus className="size-4" />فتح أول مكتب</Button>} />
      ) : view === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {pager.slice.map((m) => (
            <Card key={m.id}>
              <CardBody className="flex flex-col gap-2.5 py-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  {m.is_blocked ? (
                    <Badge status="cancelled">محظور</Badge>
                  ) : m.is_suspended ? (
                    <Badge status="pending">موقوف مؤقتاً</Badge>
                  ) : (
                    <Badge status="accepted">نشط</Badge>
                  )}
                  <span dir="ltr" className="tnum ms-auto text-sm text-muted">{m.office_code}</span>
                </div>
                <Link href={`/office/members/${m.id}`} className="text-lg font-bold text-brand-700 hover:underline">
                  {m.name}
                </Link>
                <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface-2/30">
                  <TxnField icon={UserRound} label="المستخدم" value={m.username} />
                  <TxnField icon={Phone} label="الهاتف" value={m.phone ? <span className="tnum">{m.phone}</span> : "—"} />
                  <TxnField icon={Mail} label="البريد" value={m.email || "—"} />
                  <TxnField icon={MessageCircle} label="مجموعة الواتساب" value={m.whatsapp_group_name || "—"} />
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>الكود</TH><TH>الاسم</TH><TH>المستخدم</TH><TH>الهاتف</TH>
              <TH>مجموعة الواتساب</TH><TH>الحالة</TH>
            </TR>
          </THead>
          <TBody>
            {pager.slice.map((m) => (
              <TR key={m.id}>
                <TD className="tnum text-sm text-muted">{m.office_code}</TD>
                <TD>
                  <Link href={`/office/members/${m.id}`} className="font-medium text-brand-700 hover:underline">
                    {m.name}
                  </Link>
                </TD>
                <TD>{m.username}</TD>
                <TD className="tnum">{m.phone || "—"}</TD>
                <TD>{m.whatsapp_group_name || "—"}</TD>
                <TD>
                  {m.is_blocked ? (
                    <Badge status="cancelled">محظور</Badge>
                  ) : m.is_suspended ? (
                    <Badge status="pending">موقوف مؤقتاً</Badge>
                  ) : (
                    <Badge status="accepted">نشط</Badge>
                  )}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
      <Pagination page={pager.page} pages={pager.pages} total={pager.total} onChange={pager.setPage} />

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
          <Input label="البريد الإلكتروني" type="email" dir="ltr"
            value={createForm.email}
            onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} />
          <Input label="اسم مجموعة الواتساب" value={createForm.whatsapp_group_name}
            onChange={(e) => setCreateForm({ ...createForm, whatsapp_group_name: e.target.value })} />
          <Input label="رابط مجموعة الواتساب" dir="ltr" placeholder="https://chat.whatsapp.com/…"
            value={createForm.whatsapp_group_link}
            onChange={(e) => setCreateForm({ ...createForm, whatsapp_group_link: e.target.value })} />
          {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
          <div className="flex justify-end gap-3 sm:col-span-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>إلغاء</Button>
            <Button type="submit"><UserPlus className="size-4" />فتح المكتب</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
