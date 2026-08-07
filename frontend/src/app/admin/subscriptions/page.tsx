"use client";

/** الاشتراكات: طلبات معلّقة → تفعيل يدوي بعد تأكيد الدفع (خارج النظام). */

import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  EmptyState,
  Skeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  Table,
  Tabs,
  type BadgeStatus,
} from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { formatDateTime } from "@/lib/format";

interface Sub {
  id: number;
  tenant_name: string;
  tenant_code: string;
  package_name: string;
  status: "pending" | "active" | "expired" | "rejected";
  requested_at: string;
  activated_at: string | null;
  expires_at: string | null;
}

const statusBadge: Record<Sub["status"], { s: BadgeStatus; label: string }> = {
  pending: { s: "pending", label: "بانتظار التفعيل" },
  active: { s: "accepted", label: "مفعّل" },
  expired: { s: "reversed", label: "منتهٍ" },
  rejected: { s: "cancelled", label: "مرفوض" },
};

function SubsTable({ subs, onAction }: { subs: Sub[]; onAction: () => void }) {
  async function act(id: number, action: "activate" | "reject") {
    await authedApi(`/api/admin/subscriptions/${id}/${action}/`, { method: "POST" });
    onAction();
  }

  if (subs.length === 0) return <EmptyState title="لا اشتراكات هنا" />;
  return (
    <Table>
      <THead>
        <TR>
          <TH>المكتب</TH>
          <TH>الباقة</TH>
          <TH>طُلب في</TH>
          <TH>ينتهي في</TH>
          <TH>الحالة</TH>
          <TH>إجراء</TH>
        </TR>
      </THead>
      <TBody>
        {subs.map((s) => (
          <TR key={s.id}>
            <TD>
              <span className="font-medium">{s.tenant_name}</span>{" "}
              <span className="tnum text-sm text-muted">({s.tenant_code})</span>
            </TD>
            <TD>{s.package_name}</TD>
            <TD className="tnum text-sm">{formatDateTime(s.requested_at)}</TD>
            <TD className="tnum text-sm">{s.expires_at ? formatDateTime(s.expires_at) : "—"}</TD>
            <TD>
              <Badge status={statusBadge[s.status].s}>{statusBadge[s.status].label}</Badge>
            </TD>
            <TD>
              {s.status === "pending" ? (
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => act(s.id, "activate")}>تفعيل</Button>
                  <Button size="sm" variant="ghost" onClick={() => act(s.id, "reject")}>رفض</Button>
                </div>
              ) : (
                "—"
              )}
            </TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Sub[] | null>(null);

  const load = useCallback(() => {
    authedApi<{ results?: Sub[] } | Sub[]>("/api/admin/subscriptions/")
      .then((d) => setSubs(Array.isArray(d) ? d : (d.results ?? [])))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  if (!subs) return <Skeleton className="h-64" />;

  const pending = subs.filter((s) => s.status === "pending");
  const rest = subs.filter((s) => s.status !== "pending");

  return (
    <Tabs
      tabs={[
        {
          key: "pending",
          label: `بانتظار التفعيل (${pending.length})`,
          content: <SubsTable subs={pending} onAction={load} />,
        },
        { key: "all", label: "الأرشيف", content: <SubsTable subs={rest} onAction={load} /> },
      ]}
    />
  );
}
