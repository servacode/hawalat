"use client";

/** تنبيهات الأدمن → المكاتب الكبيرة فقط (الجزء 16). */

import { Megaphone } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, CardBody, EmptyState, Input, Skeleton } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime } from "@/lib/format";

interface Broadcast {
  id: number;
  title: string;
  message: string;
  created_at: string;
}

export default function BroadcastsPage() {
  const [items, setItems] = useState<Broadcast[] | null>(null);
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authedApi<{ results?: Broadcast[] } | Broadcast[]>("/api/admin/broadcasts/")
      .then((d) => setItems(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await authedApi("/api/admin/broadcasts/", {
        method: "POST",
        body: { title, message },
      });
      setTitle("");
      setMessage("");
      load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardBody>
          <form onSubmit={send} className="flex flex-col gap-4">
            <Input label="العنوان" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="msg" className="text-sm font-medium">النص</label>
              <textarea
                id="msg"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
                rows={3}
                className="w-full rounded-md border border-border bg-surface px-3.5 py-2.5 text-base focus:border-brand focus:outline-2 focus:outline-brand/30"
              />
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={busy}>
                {busy ? "جارٍ الإرسال…" : (<><Megaphone className="size-4" /> بث للمكاتب الكبيرة</>)}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {!items ? (
        <Skeleton className="h-40" />
      ) : items.length === 0 ? (
        <EmptyState title="لا تنبيهات مُرسلة بعد" />
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((b) => (
            <Card key={b.id}>
              <CardBody className="flex flex-col gap-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold">{b.title}</p>
                  <p className="tnum text-sm text-muted">{formatDateTime(b.created_at)}</p>
                </div>
                <p className="text-muted">{b.message}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
