"use client";

/** تنبيهات المكتب الكبير (الجزء 16): بث لكل مكاتبه + الواردة من إدارة المنصة. */

import { Megaphone } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, CardBody, EmptyState, Input, Skeleton, Tabs } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime } from "@/lib/format";

interface Alert { id: number; title: string; message: string; at?: string; created_at?: string }

function AlertsList({ items }: { items: Alert[] | null }) {
  if (!items) return <Skeleton className="h-40" />;
  if (items.length === 0) return <EmptyState title="لا تنبيهات" />;
  return (
    <div className="flex flex-col gap-3">
      {items.map((a) => (
        <Card key={a.id}>
          <CardBody className="flex flex-col gap-1">
            <div className="flex items-center justify-between gap-3">
              <p className="font-bold">{a.title}</p>
              <p className="tnum text-sm text-muted">{formatDateTime(a.at ?? a.created_at ?? "")}</p>
            </div>
            <p className="text-muted">{a.message}</p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function SendTab() {
  const [mine, setMine] = useState<Alert[] | null>(null);
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authedApi<Alert[]>("/api/office/alerts/").then(setMine).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await authedApi("/api/office/alerts/", { method: "POST", body: { title, message } });
      setTitle("");
      setMessage("");
      load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardBody>
          <form onSubmit={send} className="flex flex-col gap-4">
            <Input label="العنوان" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="msg" className="text-sm font-medium">النص</label>
              <textarea id="msg" rows={3} value={message} required
                onChange={(e) => setMessage(e.target.value)}
                className="w-full rounded-md border border-border bg-surface px-3.5 py-2.5 text-base focus:border-brand focus:outline-2 focus:outline-brand/30" />
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={busy}>
                {busy ? "جارٍ…" : (<><Megaphone className="size-4" /> بث لكل مكاتبي</>)}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
      <AlertsList items={mine} />
    </div>
  );
}

function InboxTab() {
  const [items, setItems] = useState<Alert[] | null>(null);
  useEffect(() => {
    authedApi<Alert[]>("/api/office/broadcasts/").then(setItems).catch(() => setItems([]));
  }, []);
  return <AlertsList items={items} />;
}

export default function OfficeAlertsPage() {
  return (
    <Tabs
      tabs={[
        { key: "send", label: "بث لمكاتبي", content: <SendTab /> },
        { key: "inbox", label: "الواردة من المنصة", content: <InboxTab /> },
      ]}
    />
  );
}
