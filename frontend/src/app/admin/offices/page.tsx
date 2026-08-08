"use client";

/** إدارة المكاتب الكبيرة: فتح/تعديل/حظر/تفعيل/استعادة كلمة مرور — بلا أموال. */

import { Ban, Building2, CircleCheck, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, EmptyState, Input, Modal, PasswordInput, Skeleton, TBody, TD, TH, THead, TR, Table } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";

interface Office {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  small_offices_count: number;
  owner_username: string;
  owner_phone: string;
  active_package: string | null;
}

export default function OfficesPage() {
  const [offices, setOffices] = useState<Office[] | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", username: "", password: "", phone: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authedApi<Office[]>("/api/admin/offices/").then(setOffices).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function createOffice(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authedApi("/api/admin/offices/", { method: "POST", body: form });
      setCreateOpen(false);
      setForm({ name: "", username: "", password: "", phone: "" });
      load();
    } catch {
      setError("تعذر الإنشاء — تأكد من البيانات (اسم مستخدم غير مكرر، كلمة مرور 8+).");
    } finally {
      setBusy(false);
    }
  }

  async function toggleBlock(o: Office) {
    await authedApi(`/api/admin/offices/${o.id}/${o.is_active ? "block" : "unblock"}/`, {
      method: "POST",
    });
    load();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-muted">فتح المكاتب الكبيرة وإدارتها — الأدمن حصراً.</p>
        <Button onClick={() => setCreateOpen(true)}><Plus className="size-4" /> مكتب كبير جديد</Button>
      </div>

      {!offices ? (
        <Skeleton className="h-64" />
      ) : offices.length === 0 ? (
        <EmptyState
          title="لا مكاتب بعد"
          description="ابدأ بفتح أول مكتب كبير."
          action={<Button onClick={() => setCreateOpen(true)}><Building2 className="size-4" /> فتح مكتب</Button>}
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>الكود</TH>
              <TH>الاسم</TH>
              <TH>المستخدم</TH>
              <TH>الهاتف</TH>
              <TH>المكاتب الصغيرة</TH>
              <TH>الباقة</TH>
              <TH>الحالة</TH>
              <TH>إجراء</TH>
            </TR>
          </THead>
          <TBody>
            {offices.map((o) => (
              <TR key={o.id}>
                <TD className="tnum text-sm text-muted">{o.code}</TD>
                <TD className="font-medium">{o.name}</TD>
                <TD>{o.owner_username}</TD>
                <TD className="tnum">{o.owner_phone || "—"}</TD>
                <TD className="tnum">{o.small_offices_count}</TD>
                <TD>{o.active_package ?? "—"}</TD>
                <TD>
                  {o.is_active ? (
                    <Badge status="accepted">نشط</Badge>
                  ) : (
                    <Badge status="cancelled">محظور</Badge>
                  )}
                </TD>
                <TD>
                  <Button
                    size="sm"
                    variant={o.is_active ? "danger" : "primary"}
                    onClick={() => toggleBlock(o)}
                  >
                    {o.is_active ? (<><Ban className="size-4" /> حظر</>) : (<><CircleCheck className="size-4" /> تفعيل</>)}
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="فتح مكتب كبير جديد"
      >
        <form onSubmit={createOffice} className="flex flex-col gap-4">
          <Input
            label="اسم المكتب"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <Input
            label="اسم المستخدم"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <PasswordInput
            label="كلمة المرور"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            hint="8 أحرف على الأقل"
            required
          />
          <Input
            label="رقم هاتف واتساب"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              إلغاء
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "جارٍ الإنشاء…" : (<><Building2 className="size-4" /> فتح المكتب</>)}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
