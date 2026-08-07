# مشروع حوالات — المخططات المعمارية (Architecture Diagrams)

> مخططات مرئية تلخّص كل ما سُجّل في `00-discovery-notes.md`.
> تُقرأ مع الدفتر، وتتحدّث معه كلما تغيّرت الرؤية.

---

## 1) الأدوار والهرمية والباقات (Roles · Tenancy · Subscriptions)

```mermaid
flowchart TD
    subgraph PLATFORM["طبقة المنصة SaaS"]
        ADMIN["الأدمن / صاحب المنصة<br/>إداري بحت — لا علاقة مالية"]
        PKG["الباقات<br/>حد أقصى لعدد المكاتب الصغيرة"]
    end

    subgraph T1["مستأجر 1 — بيانات معزولة"]
        BO1["مكتب كبير A<br/>مستخدم واحد"]
        SO1["مكتب صغير A-1"]
        SO2["مكتب صغير A-2"]
    end

    subgraph T2["مستأجر 2 — بيانات معزولة"]
        BO2["مكتب كبير B<br/>مستخدم واحد"]
        SO3["مكتب صغير B-1"]
    end

    ADMIN -->|يبيع ويفعّل| PKG
    ADMIN -->|يفتح / يعدّل / يحظر| BO1
    ADMIN -->|يفتح / يعدّل / يحظر| BO2
    PKG -.->|يشترى لتفعيل فتح المكاتب| BO1
    PKG -.->|يشترى| BO2
    BO1 -->|يفتح ضمن حدّ الباقة| SO1
    BO1 -->|يفتح ضمن حدّ الباقة| SO2
    BO2 --> SO3
    SO1 -->|يرسل حركات| BO1
    SO2 -->|يرسل حركات| BO1
    SO3 -->|يرسل حركات| BO2

    classDef admin fill:#1e3a8a,color:#fff,stroke:#1e3a8a
    classDef big fill:#065f46,color:#fff,stroke:#065f46
    classDef small fill:#7c2d12,color:#fff,stroke:#7c2d12
    classDef pkg fill:#78350f,color:#fff,stroke:#78350f
    class ADMIN admin
    class BO1,BO2 big
    class SO1,SO2,SO3 small
    class PKG pkg
```

**ملاحظات:**
- كل **مكتب كبير = مستأجر (Tenant)** ببيانات معزولة تماماً.
- **الأدمن** لا يرى المال؛ يدير المكاتب الكبيرة والباقات فقط.
- **المكاتب الصغيرة مجانية** (لا دفع)، لكن عددها محكوم بباقة المكتب الكبير.
- **الفرد = المكتب الصغير** (نفس الكيان: مستخدم تابع لمكتب كبير).

---

## 2) دورة حياة الحركة (Transaction Lifecycle)

```mermaid
stateDiagram-v2
    state "قيد الانتظار" as pending
    state "مقبولة" as accepted
    state "ملغية" as cancelled
    state "معكوسة (عكس قيد)" as reversed

    [*] --> pending : الصغير يرسل الحركة
    pending --> accepted : الكبير يقبل + يدخل الأجور + يختار صندوق الوسيط
    pending --> cancelled : الكبير يرفض

    state accepted {
        state "غير مدفوعة" as unpaid
        state "مدفوعة" as paid
        state "لم تُسلَّم" as undelivered
        state "تم التسليم" as delivered
        [*] --> unpaid
        unpaid --> paid : تعليم كمدفوعة
        --
        [*] --> undelivered
        undelivered --> delivered : تعليم كمُسلَّمة
    }

    accepted --> reversed : تصحيح بعكس القيد
    cancelled --> [*]
    reversed --> [*]

    note right of reversed
        لا حذف نهائياً.
        التصحيح دائماً عبر عكس القيد
        الذي يعيد آثار الحركة على الصناديق.
    end note
```

**الحالات الثلاث مستقلة عن بعضها:** القبول (انتظار/مقبولة/ملغية) · الدفع (مدفوعة/غير مدفوعة) · التسليم (مُسلَّمة/غير مُسلَّمة).

---

## 3) المسار المحاسبي لحركة واحدة (Money & Ledger Flow)

```mermaid
flowchart LR
    A["🧾 مكتب صغير<br/>يُنشئ حركة<br/>مبلغ + عملة إرسال + وجهة (نص حر)"]

    A -->|تصل قيد الانتظار| B["🏢 المكتب الكبير<br/>يراجع في (الحركات الجارية)"]

    B --> C{قبول أم رفض؟}
    C -->|رفض| X["❌ ملغية"]
    C -->|قبول| D["✅ مقبولة"]

    D --> E1["📒 حساب المكتب الصغير<br/>قيد له/عليه<br/>(عملة الإرسال)"]
    D --> E2["💵 الأجور<br/>رأس مال الأجور مقابل الأجور المستحقة<br/>الربح = الفرق"]
    D --> E3["🔁 صندوق الوسيط<br/>يُنقَص بالمبلغ الممرّر<br/>(عملة الاستلام)"]
    D --> E4["🏦 صندوق المحل<br/>الكاش الفعلي (عند حركة نقدية)"]

    E1 -. سعر الصرف المثبّت بتاريخ الحركة .-> E3
    E3 -->|التنفيذ الفعلي خارج البرنامج<br/>عبر طرف ثالث يدوياً| F["🌍 المستفيد في الوجهة"]

    G["💳 تعزيز الرصيد / تسوية<br/>سند قبض/دفع (ليست حوالة)"] --> E1
    H["➕ اعتماد/دفع للوسيط"] --> E3

    classDef small fill:#7c2d12,color:#fff
    classDef big fill:#065f46,color:#fff
    classDef ledger fill:#334155,color:#fff
    class A small
    class B,C,D big
    class E1,E2,E3,E4 ledger
```

**القاعدة:** كل حركة مقبولة تولّد قيوداً متعددة (حساب الصغير + الأجور/الربح + صندوق الوسيط)، مربوطة بسعر الصرف عند اختلاف العملتين. الحد السالب لكل عملة يمنع الإرسال عند تجاوزه.

---

## 4) خريطة الأقسام حسب الدور (Navigation Map)

```mermaid
mindmap
  root((حوالات))
    الأدمن
      المكاتب الكبيرة - فتح/تعديل/حظر
      الباقات والاشتراكات
      إحصاءات غير مالية
      إعدادات المنصة
    المكتب الكبير
      الرئيسية
      الحركات الجارية
      سجل الحركات
      الحسابات - فتح/تعديل/استعادة/حظر
      صناديق المحل
      صناديق الوسطاء
      الأرباح
      الدفعات والتسويات
      كشوف الحسابات
      المطابقة
      سجل التدقيق
      التقارير
      العملات وأسعار الصرف
      التنبيهات - بث
      الإعدادات
      الإشعارات
    المكتب الصغير
      الرئيسية
      إرسال حركة
      سجل الحركات
      الصناديق - لكل عملة
      المطابقة
      التقارير
      التنبيهات - مشاهدة
      الإشعارات
      إعدادات محدودة
```

---

## 5) نموذج البيانات المبدئي (Entity Relationship — Draft)

```mermaid
erDiagram
    ADMIN ||--o{ BIG_OFFICE : "يفتح ويحظر"
    ADMIN ||--o{ PACKAGE : "يعرّف"
    PACKAGE ||--o{ SUBSCRIPTION : "تُشترى كـ"
    BIG_OFFICE ||--|| SUBSCRIPTION : "لديها"
    BIG_OFFICE ||--o{ SMALL_OFFICE : "يفتح (ضمن حدّ الباقة)"
    BIG_OFFICE ||--o{ CURRENCY : "يُدير"
    BIG_OFFICE ||--o{ INTERMEDIARY_BOX : "يملك"
    BIG_OFFICE ||--o{ SHOP_CASH_BOX : "يملك"
    SMALL_OFFICE ||--o{ TRANSACTION : "يُنشئ"
    SMALL_OFFICE ||--o{ CREDIT_LIMIT : "لديه (لكل عملة)"
    TRANSACTION ||--o{ LEDGER_ENTRY : "يولّد"
    INTERMEDIARY_BOX ||--o{ LEDGER_ENTRY : "يتأثر بـ"
    SHOP_CASH_BOX ||--o{ LEDGER_ENTRY : "يتأثر بـ"
    SMALL_OFFICE ||--o{ SETTLEMENT : "تعزيز/تسوية"
    BIG_OFFICE ||--o{ BROADCAST : "يبث"
    BIG_OFFICE ||--o{ AUDIT_LOG : "يُسجّل عليه"

    ADMIN {
        string name
        string role "admin"
    }
    BIG_OFFICE {
        string name
        string office_code
        int users "1"
    }
    PACKAGE {
        string name
        int max_small_offices
        decimal price
    }
    SUBSCRIPTION {
        date start
        date end
        string status
    }
    SMALL_OFFICE {
        string name
        string office_code
        string whatsapp_group
        string phone
        string status "active/blocked"
    }
    CURRENCY {
        string code "USD/TRY/SYP/EUR"
        string name
    }
    CREDIT_LIMIT {
        string currency
        decimal negative_limit
    }
    TRANSACTION {
        string reference_code
        string sender
        string beneficiary
        decimal amount_send
        string currency_send
        decimal amount_receive
        string currency_receive
        decimal exchange_rate
        string destination "نص حر"
        decimal fee_cost "رأس مال الأجور"
        decimal fee_charged "الأجور المستحقة"
        string status_approval
        string status_payment
        string status_delivery
        datetime created_at
    }
    LEDGER_ENTRY {
        string account_ref
        decimal debit
        decimal credit
        string currency
    }
    INTERMEDIARY_BOX {
        string name
        string number
        string currencies
    }
    SHOP_CASH_BOX {
        string currency
        decimal balance
    }
    SETTLEMENT {
        string type "receipt/payment"
        decimal amount
        string currency
    }
    BROADCAST {
        string message
        datetime sent_at
    }
    AUDIT_LOG {
        string actor
        string action
        datetime at
    }
```

> ⚠️ هذا النموذج **مبدئي (Draft)** لتوضيح الرؤية فقط — لا يُعتمد للبناء قبل مرحلة التصميم التقني ومراجعته معك.

---

## 6) المبادئ الحاكمة (Governing Principles)

```mermaid
flowchart TB
    P1["🧮 أداة محاسبية أولاً<br/>السجل المالي هو العمود الفقري"]
    P2["🔒 عزل المستأجرين<br/>من أول سطر كود"]
    P3["🚫 لا حذف — عكس قيد فقط"]
    P4["🔑 دخول موحّد + صلاحيات حسب الدور (RBAC)"]
    P5["🌐 ويب أولاً + قابل للتغليف كتطبيق (PWA)"]
    P6["⚙️ الكبير يتحكم بكل شيء / الصغير تابع"]

    P1 --- P2 --- P3
    P4 --- P5 --- P6
```
