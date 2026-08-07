export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-brand text-2xl font-bold text-white shadow-lg">
        ح
      </div>
      <h1 className="text-3xl font-bold">حوالات</h1>
      <p className="max-w-md text-center text-muted">
        نظام محاسبي لإدارة الحوالات المالية بين المكاتب — قيد البناء (المرحلة 0:
        الأساسات).
      </p>
      <span className="rounded-full border border-border bg-surface px-4 py-1 text-sm text-muted">
        الإصدار التمهيدي
      </span>
    </main>
  );
}
