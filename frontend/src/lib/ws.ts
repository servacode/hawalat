/**
 * حوالات — عميل WebSocket المركزي (المرحلة 8)
 * اتصال واحد لكل جلسة؛ الأحداث تُبثّ داخلياً عبر CustomEvent موحّد
 * فتستمع أي شاشة دون فتح اتصالات إضافية. إعادة اتصال تلقائية.
 */

import { getSession, refreshSession } from "./auth";

export interface WsEvent {
  kind: "hello" | "notification" | "refresh";
  [key: string]: unknown;
}

export const WS_EVENT = "hawalat:ws";

let socket: WebSocket | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;

export function connectWs(): void {
  const session = getSession();
  if (!session || typeof window === "undefined") return;
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

  const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  socket = new WebSocket(`${base}/ws/notifications/?token=${session.access}`);

  socket.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as WsEvent;
      window.dispatchEvent(new CustomEvent<WsEvent>(WS_EVENT, { detail: data }));
    } catch {
      /* تجاهل رسالة مشوهة */
    }
  };
  socket.onclose = () => {
    socket = null;
    if (getSession()) {
      if (retryTimer) clearTimeout(retryTimer);
      // تجديد التوكن قبل إعادة الاتصال (جلسات WS الطويلة — دين م8)
      retryTimer = setTimeout(async () => {
        await refreshSession();
        connectWs();
      }, 3000);
    }
  };
}

export function disconnectWs(): void {
  if (retryTimer) clearTimeout(retryTimer);
  retryTimer = null;
  socket?.close();
  socket = null;
}

/** استماع مبسّط: يعيد دالة إلغاء. */
export function onWsEvent(handler: (e: WsEvent) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<WsEvent>).detail);
  window.addEventListener(WS_EVENT, listener);
  return () => window.removeEventListener(WS_EVENT, listener);
}
