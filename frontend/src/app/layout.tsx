import type { Metadata } from "next";
import { Tajawal } from "next/font/google";
import "./globals.css";

// خط الواجهة الموحّد — يُستهلك عبر متغيّر CSS من طبقة التوكِنز
const tajawal = Tajawal({
  variable: "--font-tajawal",
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "حوالات",
  description: "نظام محاسبي لإدارة الحوالات المالية بين المكاتب",
  manifest: "/manifest.json",
  icons: { icon: "/icon.svg" },
};

export const viewport = {
  themeColor: "#0d9488",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl">
      <body className={`${tajawal.variable} antialiased`}>{children}</body>
    </html>
  );
}
