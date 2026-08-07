"use client";

/** رئيسية المكتب الكبير: لمحة سريعة — الجارية وبقية الأقسام تُثرى في المراحل القادمة. */

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button, Card, CardBody, Skeleton, StatCard } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";

export default function OfficeHome() {
  const [pendingCount, setPendingCount] = useState<number | null>(null);

  useEffect(() => {
    authedApi<unknown[]>("/api/office/transactions/pending/")
      .then((d) => setPendingCount(d.length))
      .catch(() => setPendingCount(0));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {pendingCount === null ? (
          <Skeleton className="h-28" />
        ) : (
          <StatCard
            title="حركات قيد الانتظار"
            value={String(pendingCount)}
            tone={pendingCount > 0 ? "profit" : "neutral"}
            detail={pendingCount > 0 ? "تحتاج قرارك" : "لا شيء معلّق"}
          />
        )}
      </div>
      <Card>
        <CardBody className="flex items-center justify-between gap-4">
          <p className="text-muted">عالج الحركات الواردة من مكاتبك الصغيرة.</p>
          <Link href="/office/pending"><Button>فتح الحركات الجارية</Button></Link>
        </CardBody>
      </Card>
    </div>
  );
}
