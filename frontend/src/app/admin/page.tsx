"use client";

/** الرئيسية: إحصاءات غير مالية حصراً (الجزء 18). */

import { useEffect, useState } from "react";
import { Skeleton, StatCard } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";

interface Stats {
  big_offices_total: number;
  big_offices_active: number;
  big_offices_blocked: number;
  small_offices_total: number;
  pending_subscriptions: number;
  expiring_soon: number;
  transactions_total: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    authedApi<Stats>("/api/admin/stats/").then(setStats).catch(() => {});
  }, []);

  if (!stats)
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="المكاتب الكبيرة" value={String(stats.big_offices_total)} />
        <StatCard
          title="النشطة"
          value={String(stats.big_offices_active)}
          tone="pos"
        />
        <StatCard
          title="المحظورة"
          value={String(stats.big_offices_blocked)}
          tone={stats.big_offices_blocked > 0 ? "neg" : "neutral"}
        />
        <StatCard
          title="المكاتب الصغيرة"
          value={String(stats.small_offices_total)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="طلبات اشتراك معلّقة"
          value={String(stats.pending_subscriptions)}
          tone={stats.pending_subscriptions > 0 ? "profit" : "neutral"}
          detail={stats.pending_subscriptions > 0 ? "بانتظار تفعيلك" : undefined}
        />
        <StatCard title="تنتهي خلال أسبوع" value={String(stats.expiring_soon)} />
        <StatCard title="إجمالي الحركات" value={String(stats.transactions_total)} detail="رقم مجرّد — لا تفاصيل مالية" />
      </div>
    </div>
  );
}
