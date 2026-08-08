"use client";

/**
 * إعدادات المكتب الكبير — ربط رقم الواتساب (ملاحظة 44):
 * امسح QR مرة واحدة من هاتفك، وبعدها المطابقات والحركات تُرسل
 * مباشرة من رقمك بلا فتح أي رابط. + سجل الرسائل المُرسلة.
 */

import { Link2, MessageCircle, QrCode, RefreshCw, Unlink } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Skeleton } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";

interface LinkState {
  configured: boolean;
  status: string;
  number: string;
  qr: string | null;
  detail?: string;
}
export default function OfficeSettingsPage() {
  const [link, setLink] = useState<LinkState | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authedApi<LinkState>("/api/office/whatsapp/link/").then(setLink).catch(() => {});
  }, []);
  useEffect(load, [load]);

  // ريثما يُمسح الرمز: تحديث تلقائي كل 4 ثوانٍ (الـQR يتجدد والحالة تتقلب)
  useEffect(() => {
    if (!link || !["SCAN_QR_CODE", "STARTING"].includes(link.status)) return;
    const id = setInterval(() => {
      authedApi<LinkState>("/api/office/whatsapp/link/").then(setLink).catch(() => {});
    }, 4000);
    return () => clearInterval(id);
  }, [link]);

  async function startLink() {
    setBusy(true);
    try {
      const d = await authedApi<LinkState>("/api/office/whatsapp/link/", { method: "POST" });
      setLink(d);
    } catch {
      load();
    } finally {
      setBusy(false);
    }
  }

  async function unlink() {
    setBusy(true);
    try {
      await authedApi("/api/office/whatsapp/link/", { method: "DELETE" });
      load();
    } finally {
      setBusy(false);
    }
  }

  if (!link) return <Skeleton className="h-64" />;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="size-5 text-brand" /> ربط الواتساب
          </CardTitle>
        </CardHeader>
        <CardBody className="flex flex-col gap-4">
          <p className="text-sm text-muted">
            اربط رقم واتساب مكتبك بمسح رمز QR مرة واحدة — وبعدها «إرسال مطابقة»
            والحركات الجديدة تنزل للمكاتب مباشرة من رقمك بلا فتح أي رابط.
          </p>

          {!link.configured ? (
            <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
              خادم الواتساب لم يُضبط بعد من إدارة المنصة — الإرسال يبقى يدوياً بالرابط
              حتى يُفعَّل عند النشر.
            </p>
          ) : link.status === "WORKING" ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="flex items-center gap-2">
                <Badge status="accepted">مربوط</Badge>
                <span dir="ltr" className="tnum font-medium">+{link.number}</span>
              </p>
              <Button variant="danger" disabled={busy} onClick={unlink}>
                <Unlink className="size-4" /> فك الربط
              </Button>
            </div>
          ) : link.status === "SCAN_QR_CODE" ? (
            <div className="flex flex-col items-center gap-3">
              {link.qr ? (
                // eslint-disable-next-line @next/next/no-img-element -- QR لحظي من الخادم
                <img src={link.qr} alt="رمز QR لربط الواتساب" className="size-56 rounded-xl border border-border bg-white p-2" />
              ) : (
                <Skeleton className="size-56" />
              )}
              <ol className="list-inside list-decimal text-sm text-muted">
                <li>افتح واتساب في هاتفك</li>
                <li>الإعدادات ← الأجهزة المرتبطة ← ربط جهاز</li>
                <li>امسح الرمز أعلاه — يتجدد تلقائياً</li>
              </ol>
            </div>
          ) : link.status === "STARTING" ? (
            <p className="flex items-center gap-2 text-sm text-muted">
              <RefreshCw className="size-4 animate-spin" /> جارٍ تجهيز الجلسة…
            </p>
          ) : link.status === "OFFLINE" ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-danger">تعذر الوصول لخادم الواتساب — حاول لاحقاً.</p>
              <Button variant="ghost" disabled={busy} onClick={load}><RefreshCw className="size-4" /> إعادة المحاولة</Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="flex items-center gap-2 text-sm">
                <Badge status="pending">غير مربوط</Badge>
                <span className="text-muted">الإرسال حالياً يدوي بالرابط.</span>
              </p>
              <Button disabled={busy} onClick={startLink}>
                <QrCode className="size-4" /> ربط رقمي الآن
              </Button>
            </div>
          )}

          <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
            <Link2 className="mb-0.5 inline size-4" /> وجهة الإرسال لكل مكتب صغير: مجموعته
            إن كانت مضبوطة، وإلا رقم هاتفه مباشرة.
          </p>
        </CardBody>
      </Card>

    </div>
  );
}
