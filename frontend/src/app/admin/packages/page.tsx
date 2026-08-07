"use client";

/** الباقات: تعريف حدود (مكاتب + حركات) وسعر ومدة. */

import { useCallback, useEffect, useState } from "react";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Skeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  Table,
  Badge,
} from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatMoney } from "@/lib/format";

interface Package {
  id: number;
  name: string;
  max_small_offices: number;
  max_transactions: number;
  price: string;
  currency: string;
  duration_days: number;
  is_active: boolean;
}

const emptyForm = {
  name: "",
  max_small_offices: "10",
  max_transactions: "1000",
  price: "50",
  currency: "USD",
  duration_days: "30",
};

export default function PackagesPage() {
  const [packages, setPackages] = useState<Package[] | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    authedApi<{ results?: Package[] } | Package[]>("/api/admin/packages/")
      .then((d) => setPackages(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function createPackage(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await authedApi("/api/admin/packages/", { method: "POST", body: form });
      setOpen(false);
      setForm(emptyForm);
      load();
    } catch {
      setError("تعذر الحفظ — تأكد من القيم.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-muted">حدود الباقة تسري على ما يُنشأ بعد التفعيل فقط (قاعدة الترحيل).</p>
        <Button onClick={() => setOpen(true)}>+ باقة جديدة</Button>
      </div>

      {!packages ? (
        <Skeleton className="h-48" />
      ) : packages.length === 0 ? (
        <EmptyState title="لا باقات بعد" action={<Button onClick={() => setOpen(true)}>إنشاء باقة</Button>} />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>الاسم</TH>
              <TH>حد المكاتب</TH>
              <TH>حد الحركات</TH>
              <TH>السعر</TH>
              <TH>المدة</TH>
              <TH>الحالة</TH>
            </TR>
          </THead>
          <TBody>
            {packages.map((p) => (
              <TR key={p.id}>
                <TD className="font-medium">{p.name}</TD>
                <TD className="tnum">{p.max_small_offices}</TD>
                <TD className="tnum">{p.max_transactions}</TD>
                <TD className="tnum font-bold">{formatMoney(p.price, p.currency)}</TD>
                <TD className="tnum">{p.duration_days} يوم</TD>
                <TD>
                  {p.is_active ? <Badge status="accepted">متاحة</Badge> : <Badge status="reversed">معطّلة</Badge>}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="باقة جديدة">
        <form onSubmit={createPackage} className="grid gap-4 sm:grid-cols-2">
          <Input label="الاسم" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="sm:col-span-2" />
          <Input label="حد المكاتب الصغيرة" type="number" min={1} value={form.max_small_offices} onChange={(e) => setForm({ ...form, max_small_offices: e.target.value })} required />
          <Input label="حد الحركات" type="number" min={1} value={form.max_transactions} onChange={(e) => setForm({ ...form, max_transactions: e.target.value })} required />
          <Input label="السعر" type="number" min={0} step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required />
          <Input label="المدة (أيام)" type="number" min={1} value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: e.target.value })} required />
          {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
          <div className="flex justify-end gap-3 sm:col-span-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>إلغاء</Button>
            <Button type="submit">حفظ الباقة</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
