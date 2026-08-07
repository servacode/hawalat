"use client";

/** الجذر: توجيه فوري — جلسة قائمة → واجهة الدور؛ لا جلسة → الدخول. */

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getSession, roleHome } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const s = getSession();
    router.replace(s ? roleHome(s.user.role) : "/login");
  }, [router]);
  return null;
}
