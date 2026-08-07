/**
 * حوالات — نصوص الواجهة المركزية (عربي أولاً — ق5)
 * كل نص ظاهر للمستخدم يعيش هنا. إضافة لغة لاحقاً = ملف مواز لهذا الهيكل.
 */
export const ar = {
  appName: "حوالات",
  appDescription: "نظام محاسبي لإدارة الحوالات المالية بين المكاتب",
  common: {
    save: "حفظ",
    cancel: "إلغاء",
    confirm: "تأكيد",
    close: "إغلاق",
    search: "بحث",
    filter: "تصفية",
    export: "تصدير",
    loading: "جارٍ التحميل…",
    noResults: "لا توجد نتائج",
  },
  transaction: {
    sender: "اسم المرسِل",
    beneficiary: "اسم المستفيد",
    amount: "المبلغ",
    currency: "العملة",
    destination: "الوجهة",
    exchangeRate: "سعر الصرف",
    reference: "الرقم المرجعي",
    feeCost: "رأس مال الأجور",
    feeCharged: "الأجور المستحقة",
    send: "إرسال الحركة",
    sendWhatsApp: "إرسال للواتساب",
    approve: "قبول",
    reject: "رفض",
  },
  balance: {
    forUs: "لنا",
    onUs: "علينا",
    net: "الصافي",
  },
} as const;

export type Messages = typeof ar;
