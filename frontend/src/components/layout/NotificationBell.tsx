"use client";

/** جرس الإشعارات المركزي (الجزء 20-أ): شارة رقمية + قائمة + قراءة الكل — لحظي. */

import { useCallback, useEffect, useRef, useState } from "react";
import { authedApi } from "@/lib/authedApi";
import { connectWs, onWsEvent } from "@/lib/ws";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/cn";
import { Bell } from "lucide-react";

interface Notif {
  id: number; ntype: string; title: string; body: string;
  is_read: boolean; at: string;
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<Notif[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    authedApi<{ unread: number; items: Notif[] }>("/api/notifications/")
      .then((d) => {
        setUnread(d.unread);
        setItems(d.items);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    connectWs();
    load();
    return onWsEvent((e) => {
      if (e.kind === "hello") setUnread((e.unread as number) ?? 0);
      if (e.kind === "notification") {
        setUnread((e.unread as number) ?? 0);
        load();
      }
    });
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const close = (ev: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(ev.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  async function readAll() {
    const d = await authedApi<{ unread: number }>("/api/notifications/read-all/", { method: "POST" });
    setUnread(d.unread);
    load();
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen(!open)}
        aria-label={`الإشعارات — ${unread} غير مقروء`}
        className="relative rounded-md p-2 transition-colors hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-brand"
      >
        <Bell className="size-5" aria-hidden="true" />
        {unread > 0 && (
          <span className="tnum absolute -top-0.5 -start-0.5 flex size-5 items-center justify-center rounded-full bg-danger text-xs font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute start-0 top-full z-50 mt-2 w-80 rounded-lg border border-border bg-surface shadow-lg">
          <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
            <p className="font-bold">الإشعارات</p>
            {unread > 0 && (
              <button onClick={readAll} className="text-sm text-brand-700 hover:underline">
                قراءة الكل
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-center text-muted">لا إشعارات بعد</p>
            ) : (
              items.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "border-b border-border px-4 py-3 last:border-b-0",
                    !n.is_read && "bg-brand/5",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className={cn("text-sm", !n.is_read && "font-bold")}>{n.title}</p>
                    {!n.is_read && <span className="mt-1 size-2 shrink-0 rounded-full bg-brand" />}
                  </div>
                  {n.body && <p className="mt-0.5 text-sm text-muted">{n.body}</p>}
                  <p className="tnum mt-1 text-xs text-muted">{formatDateTime(n.at)}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
