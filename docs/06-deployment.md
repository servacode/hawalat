# مشروع حوالات — دليل النشر والتشغيل (Deployment Guide)

> خطوات نشر المنصة على خادم إنتاج، من الصفر حتى التشغيل الكامل مع بوت الواتساب والنسخ الاحتياطي.

---

## 1. المتطلبات

- خادم Linux (يُنصح Ubuntu 22.04+) بذاكرة 2GB+ ومعالجين.
- **Docker + Docker Compose v2** مثبّتان.
- اسما نطاق (أو نطاق فرعيان) موجّهان للخادم:
  - `app.example.com` → الواجهة (3000)
  - `api.example.com` → الباكند (8000، يشمل WebSockets)

---

## 2. الإعداد

```bash
git clone <REPO_URL> hawalat && cd hawalat
cp .env.example .env
```

عدّل `.env` بقيم **إنتاجية**:

```env
# Django — إلزامي
DJANGO_SECRET_KEY=<سلسلة عشوائية طويلة — python -c "import secrets;print(secrets.token_urlsafe(64))">
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com

# قاعدة البيانات — كلمة قوية إلزامية
POSTGRES_PASSWORD=<كلمة-قوية>

# عناوين الواجهة العامة (تُبنى داخل صورة الواجهة)
PUBLIC_API_URL=https://api.example.com
PUBLIC_WS_URL=wss://api.example.com
```

> `POSTGRES_HOST` و`REDIS_URL` يضبطهما compose تلقائياً — لا تضفهما.

---

## 3. التشغيل

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

يشغّل: **db + redis + backend (Daphne: HTTP+WS) + worker + beat + frontend**، والترحيلات تجري تلقائياً.

**إنشاء أدمن المنصة (مرة واحدة):**

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py createplatformadmin --username admin
```

---

## 4. البروكسي العاكس (TLS)

الخدمتان مربوطتان على `127.0.0.1` فقط — يلزم بروكسي أمامهما. مثال **Caddy** (تلقائي الشهادات):

```caddy
app.example.com {
    reverse_proxy 127.0.0.1:3000
}
api.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

> Caddy يمرّر WebSockets تلقائياً. مع Nginx أضف ترويسات Upgrade/Connection لمسار `/ws/`.

---

## 5. الواتساب المباشر — ربط رقم كل مكتب (ملاحظة 44)

1. شغّل خادم **WAHA** واحد للمنصة:
   ```bash
   docker run -d --name waha --restart=always -p 127.0.0.1:3001:3000 \
     -e WHATSAPP_API_KEY=ضع-مفتاحاً-قوياً devlikeapro/waha
   ```
2. **الأدمن ← إعدادات المنصة ← خادم الواتساب (WAHA)**: ضع العنوان
   (مثل `http://127.0.0.1:3001`) والمفتاح نفسه، واحفظ.
3. **كل مكتب كبير** يفتح **الإعدادات ← ربط الواتساب** ويضغط «ربط رقمي الآن»
   ثم يمسح رمز QR بهاتفه (واتساب ← الأجهزة المرتبطة) — مرة واحدة.
4. انتهى: «إرسال مطابقة» والحركات الجديدة تنزل مباشرة **من رقم المكتب نفسه** —
   لمجموعة المكتب الصغير إن ضُبطت وإلا لرقم هاتفه، بلا فتح أي رابط.
5. تحقق من **سجل الرسائل المُرسلة** في إعدادات المكتب.

> الخادم غير مضبوط أو الرقم غير مربوط = الوضع اليدوي بالرابط — لا شيء ينكسر.

---

## 6. النسخ الاحتياطي

نسخة يومية لقاعدة البيانات (cron الساعة 2 صباحاً):

```bash
crontab -e
# أضف:
0 2 * * * cd /path/to/hawalat && docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U hawalat hawalat | gzip > /backups/hawalat-$(date +\%F).sql.gz
```

احتفظ بالنسخ خارج الخادم أيضاً (rsync/S3). **الاستعادة:**

```bash
gunzip -c backup.sql.gz | docker compose -f docker-compose.prod.yml exec -T db \
  psql -U hawalat hawalat
```

---

## 7. التحديثات

```bash
cd hawalat && git pull
docker compose -f docker-compose.prod.yml up -d --build   # يعيد بناء المتغيّر فقط
```

الترحيلات تجري تلقائياً عند إقلاع الباكند. **لا حاجة لإيقاف الخدمة.**

---

## 8. المهام الدورية (مضمّنة — خدمة beat)

| المهمة | التوقيت | الوظيفة |
|---|---|---|
| `expire_subscriptions` | يومياً 00:15 | تعليم الاشتراكات المنتهية + إشعار أصحابها |
| `flush_expired_tokens` | يومياً 01:00 | تنظيف جدول التوكنات المبطَلة |

---

## 9. الفحص بعد النشر (Checklist)

- [ ] `https://api.example.com/api/health/` → `{"status": "ok"}`
- [ ] الدخول من `https://app.example.com` بالأدمن يعمل
- [ ] فتح مكتب كبير → دخوله → فتح مكتب صغير → إرسال حركة → قبولها
- [ ] الجرس اللحظي يعمل (أي أن WSS يمر عبر البروكسي)
- [ ] تصدير PDF/Excel يعمل
- [ ] النسخ الاحتياطي الليلي يكتب ملفات فعلاً

---

## 10. استكشاف الأخطاء

```bash
docker compose -f docker-compose.prod.yml logs -f backend   # سجلات الباكند
docker compose -f docker-compose.prod.yml logs -f worker    # مهام الخلفية/الواتساب
docker compose -f docker-compose.prod.yml exec backend python manage.py shell
```

| العرض | السبب الأرجح |
|---|---|
| 400 على كل الطلبات | `DJANGO_ALLOWED_HOSTS` لا يشمل نطاق الـAPI |
| الواجهة لا تصل للـAPI | `CORS_ALLOWED_ORIGINS` أو `PUBLIC_API_URL` خاطئ (يتطلب إعادة بناء الواجهة) |
| الجرس لا يعمل | البروكسي لا يمرّر WebSocket لمسار `/ws/` |
| رسائل البوت "فشلت" | عنوان البوابة/الرمز خاطئ أو جلسة QR انتهت — راجع سجل الرسائل |
