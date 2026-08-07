"use client";

/** تنبيهات المكتب الصغير: مشاهدة القادمة من مكتبه الكبير (الجزء 16). */

import { useEffect, useState } from "react";
import { Card, CardBody, EmptyState, Skeleton } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime } from "@/lib/format";
import { onWsEvent } from "@/lib/ws";

interface Alert { id: number; title: string; message: string; at: string }

export default function SmallAlertsPage() {
  const [items, setItems] = useState<Alert[] | null>(null);

  useEffect(() => {
    const load = () =>
      authedApi<Alert[]>("/api/small/alerts/").then(setItems).catch(() => setItems([]));
    load();
    return onWsEvent((e) => {
      if (e.kind === "notification" && e.ntype === "broadcast") load();
    });
  }, []);

  if (!items) return <Skeleton className="h-40" />;
  if (items.length === 0)
    return <EmptyState title="لا تنبيهات من مكتبك بعد" description="ستصلك هنا لحظياً عند بثّها." />;

  return (
    <div className="flex max-w-2xl flex-col gap-3">
      {items.map((a) => (
        <Card key={a.id}>
          <CardBody className="flex flex-col gap-1">
            <div className="flex items-center justify-between gap-3">
              <p className="font-bold">📢 {a.title}</p>
              <p className="tnum text-sm text-muted">{formatDateTime(a.at)}</p>
            </div>
            <p className="text-muted">{a.message}</p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
