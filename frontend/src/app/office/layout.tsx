"use client";

import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell, type NavItem } from "@/components/layout/Shell";

const NAV: NavItem[] = [
  { href: "/office", label: "الرئيسية", icon: "📊" },
  { href: "/office/pending", label: "الحركات الجارية", icon: "📥" },
  { href: "/office/transactions", label: "سجل الحركات", icon: "📚" },
  { href: "/office/members", label: "الحسابات", icon: "👥" },
  { href: "/office/boxes", label: "الصناديق", icon: "🏦" },
  { href: "/office/reports", label: "التقارير", icon: "📈" },
  { href: "/office/alerts", label: "التنبيهات", icon: "📢" },
];

export default function OfficeLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="big_office">
      {(session) => (
        <Shell
          title={session.user.tenant_name ?? "المكتب الكبير"}
          subtitle={session.user.office_code}
          nav={NAV}
        >
          {children}
        </Shell>
      )}
    </RoleGuard>
  );
}
