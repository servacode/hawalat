"use client";

import { LogoutButton, RoleGuard } from "@/components/auth/RoleGuard";
import { Card, CardBody } from "@/components/ui";

export default function OfficeHome() {
  return (
    <RoleGuard role="big_office">
      {(session) => (
        <main className="mx-auto flex max-w-4xl flex-col gap-6 px-5 py-10">
          <header className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                {session.user.tenant_name ?? "المكتب الكبير"}
              </h1>
              <p className="text-muted">
                الكود: <span className="tnum">{session.user.office_code}</span>
              </p>
            </div>
            <LogoutButton />
          </header>
          <Card>
            <CardBody>
              <p className="text-muted">
                الحركات الجارية والصناديق والحسابات — تُبنى بدءاً من المرحلة 4.
              </p>
            </CardBody>
          </Card>
        </main>
      )}
    </RoleGuard>
  );
}
