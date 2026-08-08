"use client";

/**
 * إعدادات المكتب الكبير — قسم الواتساب (الجزء 17 §6):
 * مفتاح البوت: مفعّل → إرسال تلقائي عبر البوابة؛ مطفأ → الرابط اليدوي.
 * + سجل رسائل البوت (تشخيص).
 */

import { Lightbulb, Save } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, EmptyState, Input, Skeleton, TBody, TD, TH, THead, TR, Table } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime } from "@/lib/format";

interface WaSettings {
  bot_enabled: boolean;
  gateway_url: string;
  has_token: boolean;
  is_ready: boolean;
}
interface OutMsg {
  id: number; to: string; chat_id: string; text: string;
  status: "pending" | "sent" | "failed"; attempts: number; error: string; at: string;
}

export default function OfficeSettingsPage() {
  const [wa, setWa] = useState<WaSettings | null>(null);
  const [gatewayUrl, setGatewayUrl] = useState("");
  const [token, setToken] = useState("");
  const [saved, setSaved] = useState(false);
  const [outbox, setOutbox] = useState<OutMsg[] | null>(null);

  const load = useCallback(() => {
    authedApi<WaSettings>("/api/office/whatsapp/").then((d) => {
      setWa(d);
      setGatewayUrl(d.gateway_url);
    }).catch(() => {});
    authedApi<OutMsg[]>("/api/office/whatsapp/outbox/").then(setOutbox).catch(() => setOutbox([]));
  }, []);
  useEffect(load, [load]);

  async function save(patch: Partial<{ bot_enabled: boolean; gateway_url: string; gateway_token: string }>) {
    const d = await authedApi<WaSettings>("/api/office/whatsapp/", { method: "PATCH", body: patch });
    setWa(d);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  if (!wa) return <Skeleton className="h-64" />;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>واتساب — وضع البوت</CardTitle>
        </CardHeader>
        <CardBody className="flex flex-col gap-4">
          <label className="flex cursor-pointer items-start justify-between gap-4">
            <span>
              <span className="block font-medium">تفعيل بوت الإرسال التلقائي</span>
              <span className="block text-sm text-muted">
                مفعّل: الحركات والمطابقات تُرسل فوراً لمجموعات المكاتب عبر البوابة.
                مطفأ: الإرسال يدوي عبر رابط المجموعة (الوضع الافتراضي — خصوصية أعلى).
              </span>
            </span>
            <input type="checkbox" checked={wa.bot_enabled}
              onChange={(e) => save({ bot_enabled: e.target.checked })}
              className="mt-1 size-5 shrink-0 accent-(--brand-600)" />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="عنوان بوابة الواتساب" dir="ltr" placeholder="https://gateway.example.com/api/send"
              value={gatewayUrl} onChange={(e) => setGatewayUrl(e.target.value)}
              hint="بوابة HTTP متوافقة (مثل WAHA) — POST {chatId, text}" />
            <Input label="رمز البوابة (Token)" dir="ltr" type="password"
              placeholder={wa.has_token ? "•••••• (محفوظ)" : ""}
              value={token} onChange={(e) => setToken(e.target.value)} />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm">
              الجاهزية:{" "}
              {wa.is_ready ? (
                <Badge status="accepted">جاهز — الإرسال تلقائي</Badge>
              ) : (
                <Badge status="pending">يدوي بالرابط</Badge>
              )}
            </p>
            <Button onClick={() => save({ gateway_url: gatewayUrl, ...(token ? { gateway_token: token } : {}) })}>
              <Save className="size-4" /> حفظ الإعدادات
            </Button>
          </div>
          {saved && <p className="text-sm text-success">تم الحفظ ✓</p>}
          <p className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">
            <Lightbulb className="mb-0.5 inline size-4" /> لكل مكتب صغير حقل «معرّف مجموعة البوت» في قسم الحسابات — مطلوب للإرسال التلقائي لمجموعته.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader><CardTitle>سجل رسائل البوت</CardTitle></CardHeader>
        <CardBody>
          {!outbox ? (
            <Skeleton className="h-32" />
          ) : outbox.length === 0 ? (
            <EmptyState title="لا رسائل بوت بعد" />
          ) : (
            <Table>
              <THead>
                <TR><TH>إلى</TH><TH>النص</TH><TH>الحالة</TH><TH>محاولات</TH><TH>الوقت</TH></TR>
              </THead>
              <TBody>
                {outbox.map((m) => (
                  <TR key={m.id}>
                    <TD>{m.to}</TD>
                    <TD className="max-w-56 truncate">{m.text}</TD>
                    <TD>
                      {m.status === "sent" ? <Badge status="accepted">أُرسلت</Badge>
                        : m.status === "failed" ? <Badge status="cancelled">فشلت</Badge>
                        : <Badge status="pending">قيد الإرسال</Badge>}
                    </TD>
                    <TD className="tnum">{m.attempts}</TD>
                    <TD className="tnum text-sm">{formatDateTime(m.at)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
