import { redirect } from "next/navigation";

/** رئيسية المكتب الصغير أُلغيت (ملاحظة التجربة 17) — التحويل لإرسال حركة. */
export default function SmallHome() {
  redirect("/small/send");
}
