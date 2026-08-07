"use client";

import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell, type NavItem } from "@/components/layout/Shell";

const NAV: NavItem[] = [
  { href: "/small", label: "الرئيسية", icon: "📊" },
  { href: "/small/send", label: "إرسال حركة", icon: "📤" },
  { href: "/small/transactions", label: "سجل الحركات", icon: "📚" },
  { href: "/small/boxes", label: "الصناديق", icon: "🏦" },
];

export default function SmallLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="small_office">
      {(session) => (
        <Shell
          title={session.user.first_name || session.user.username}
          subtitle={session.user.office_code}
          nav={NAV}
        >
          {children}
        </Shell>
      )}
    </RoleGuard>
  );
}
