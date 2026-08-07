"use client";

/**
 * صفحة عرض المكوّنات (Design Showcase) — مخرَج المرحلة 1
 * كل ما هنا مبني حصراً من مكتبة المكوّنات وطبقة التوكِنز — صفر تنسيق يدوي.
 */

import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
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
  Tabs,
} from "@/components/ui";
import { balanceTone, formatMoney } from "@/lib/format";

const demoRows = [
  { ref: "HW-042-1007", sender: "أحمد سالم", beneficiary: "مروان حدّاد", amount: 1000, currency: "USD", dest: "دمشق", status: "pending" as const },
  { ref: "HW-042-1006", sender: "سمير علي", beneficiary: "ليلى نعمة", amount: 7500, currency: "TRY", dest: "حلب", status: "accepted" as const },
  { ref: "HW-042-1005", sender: "خالد يوسف", beneficiary: "رنا خوري", amount: 450, currency: "EUR", dest: "إسطنبول", status: "paid" as const },
  { ref: "HW-042-1004", sender: "وسام درويش", beneficiary: "عمر شاهين", amount: 3200, currency: "USD", dest: "بيروت", status: "cancelled" as const },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-sm font-bold uppercase tracking-widest text-brand-700">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function DesignPage() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-10 px-5 py-10">
      <header className="flex flex-wrap items-center gap-4 border-b border-border pb-6">
        <div className="flex size-12 items-center justify-center rounded-xl bg-brand text-xl font-bold text-white shadow-md">
          ح
        </div>
        <div>
          <h1 className="text-2xl font-bold">حوالات — معرض المكوّنات</h1>
          <p className="text-muted">النظام المركزي: كل شيء من التوكِنز والمكتبة حصراً</p>
        </div>
      </header>

      <Section title="الأزرار">
        <div className="flex flex-wrap items-center gap-3">
          <Button>قبول الحركة</Button>
          <Button variant="ghost">عرض التفاصيل</Button>
          <Button variant="accent">إرسال مطابقة</Button>
          <Button variant="danger">رفض</Button>
          <Button disabled>معطّل</Button>
          <Button size="sm">صغير</Button>
          <Button size="lg">كبير</Button>
        </div>
      </Section>

      <Section title="حالات الحركة">
        <div className="flex flex-wrap gap-3">
          <Badge status="pending" />
          <Badge status="accepted" />
          <Badge status="cancelled" />
          <Badge status="paid" />
          <Badge status="delivered" />
          <Badge status="reversed" />
        </div>
      </Section>

      <Section title="بطاقات الإحصاء">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="صافي صندوق الدولار" value={formatMoney(12800.5)} tone={balanceTone(12800.5)} detail="لنا" />
          <StatCard title="صافي الليرة التركية" value={formatMoney(-5240.75)} tone={balanceTone(-5240.75)} detail="علينا" />
          <StatCard title="أرباح اليوم (فرق الأجور)" value={formatMoney(340)} tone="profit" detail="من 42 حركة" />
          <StatCard title="حركات قيد الانتظار" value="7" detail="تحتاج قراراً" />
        </div>
      </Section>

      <Section title="النماذج">
        <Card>
          <CardHeader>
            <CardTitle>إرسال حركة</CardTitle>
          </CardHeader>
          <CardBody className="grid gap-4 sm:grid-cols-2">
            <Input label="اسم المرسِل" placeholder="أحمد سالم" />
            <Input label="اسم المستفيد" placeholder="مروان حدّاد" />
            <Input label="المبلغ" type="number" placeholder="1000" className="tnum" />
            <Select
              label="العملة"
              placeholder="اختر العملة"
              options={[
                { value: "USD", label: "دولار أمريكي" },
                { value: "TRY", label: "ليرة تركية" },
                { value: "SYP", label: "ليرة سورية" },
                { value: "EUR", label: "يورو" },
              ]}
            />
            <Input label="الوجهة" placeholder="دمشق" hint="تُكتب يدوياً" />
            <Input label="سعر الصرف" placeholder="—" error="إلزامي عند اختلاف العملتين" />
          </CardBody>
        </Card>
      </Section>

      <Section title="جدول الحركات">
        <Table>
          <THead>
            <TR className="border-t-0 hover:bg-surface-2/0">
              <TH>المرجع</TH>
              <TH>المرسِل</TH>
              <TH>المستفيد</TH>
              <TH>المبلغ</TH>
              <TH>الوجهة</TH>
              <TH>الحالة</TH>
            </TR>
          </THead>
          <TBody>
            {demoRows.map((row) => (
              <TR key={row.ref}>
                <TD className="tnum text-sm text-muted">{row.ref}</TD>
                <TD>{row.sender}</TD>
                <TD>{row.beneficiary}</TD>
                <TD className="tnum font-bold">{formatMoney(row.amount, row.currency)}</TD>
                <TD>{row.dest}</TD>
                <TD>
                  <Badge status={row.status} />
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Section>

      <Section title="التبويبات">
        <Tabs
          tabs={[
            { key: "boxes", label: "الصناديق", content: <p className="text-muted">صندوق لكل عملة: له / عليه / الصافي.</p> },
            { key: "recon", label: "المطابقة", content: <p className="text-muted">كشف دوري تراكمي منذ آخر مطابقة.</p> },
            { key: "log", label: "السجل", content: <p className="text-muted">كل الحركات المنفّذة مع فلتر وتصدير.</p> },
          ]}
        />
      </Section>

      <Section title="حالات فارغة وتحميل">
        <div className="grid gap-4 sm:grid-cols-2">
          <EmptyState
            title="لا توجد حركات بعد"
            description="عند وصول أول حركة من مكتب صغير ستظهر هنا."
            action={<Button size="sm">إرسال حركة</Button>}
          />
          <Card className="flex flex-col gap-3 p-5">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-10 w-1/3" />
          </Card>
        </div>
      </Section>

      <Section title="النوافذ">
        <div>
          <Button variant="ghost" onClick={() => setModalOpen(true)}>
            فتح نافذة تأكيد
          </Button>
          <Modal
            open={modalOpen}
            onClose={() => setModalOpen(false)}
            title="تأكيد قبول الحركة"
            footer={
              <>
                <Button variant="ghost" onClick={() => setModalOpen(false)}>
                  إلغاء
                </Button>
                <Button onClick={() => setModalOpen(false)}>قبول</Button>
              </>
            }
          >
            <p className="text-muted">
              سيتم قبول الحركة <span className="tnum font-bold text-ink">HW-042-1007</span>{" "}
              وتوليد القيود المحاسبية على حساب المكتب الصغير وصندوق الوسيط.
            </p>
          </Modal>
        </div>
      </Section>
    </main>
  );
}
