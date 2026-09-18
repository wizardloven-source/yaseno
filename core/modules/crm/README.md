# 🎯 وحدة إدارة علاقات العملاء (CRM)

## نظرة عامة

وحدة CRM متكاملة لإدارة دورة المبيعات الكاملة من العميل المحتمل حتى الإغلاق.

## المكونات الرئيسية

### 1. **العملاء المحتملين (Leads)**
- تتبع مصادر العملاء المحتملين
- التأهيل والتحويل لفرص
- تقييم وتصنيف العملاء
- سجل تفاعلات كامل

### 2. **الفرص البيعية (Opportunities)**
- خط أنابيب مبيعات مرئي (Pipeline)
- 6 مراحل: Prospecting → Qualification → Proposal → Negotiation → Closed Won/Lost
- تتبع القيم المتوقعة والمرجحة
- ربط بعروض الأسعار وأوامر البيع

### 3. **الأنشطة (Activities)**
- مكالمات، اجتماعات، رسائل بريد
- مهام ومتابعات
- تنبيهات المواعيد النهائية

### 4. **المهام (Tasks)**
- تعيين مهام لفريق المبيعات
- تتبع الحالة والاستحقاق
- أولويات متعددة

## الهيكلية

```
crm/
├── domain/
│   ├── entities.py       # الكيانات التجارية (Lead, Opportunity, Activity, Task)
│   ├── events.py         # أحداث النطاق للتكامل
│   └── __init__.py
├── application/
│   ├── commands.py       # تعريف الأوامر
│   ├── queries.py        # تعريف الاستعلامات
│   ├── handlers/         # معالجات الأوامر والاستعلامات
│   └── __init__.py
├── infrastructure/
│   ├── models.py         # نماذج قاعدة البيانات
│   ├── repositories/     # تنفيذ المستودعات
│   └── __init__.py
└── presentation/
    ├── schemas.py        # Pydantic schemas للـ API
    ├── routers/          # FastAPI routers
    └── __init__.py
```

## التكامل مع الوحدات الأخرى

### مع المبيعات (Sales Cycle)
- تحويل Lead → Opportunity → Quote → Order
- ربط الفرص بعروض الأسعار
- تتبع أوامر البيع الناتجة عن الفرص

### مع العملاء (Customers)
- تحويل Lead المؤهل إلى عميل
- تحديث سجل تفاعلات العميل

### مع المحاسبة (Accounting)
- تحليل الربحية حسب الفرصة
- تتبع العمولات

## حالات الاستخدام

### 1. إضافة عميل محتمل جديد
```python
command = CreateLeadCommand(
    first_name="أحمد",
    last_name="محمد",
    company_name="شركة التقنية",
    email="ahmed@tech.com",
    phone="+966501234567",
    source="website",
    expected_value=50000.0
)
handler = CreateLeadHandler(repository, event_bus)
lead = await handler.handle(command)
```

### 2. تأهيل عميل محتمل
```python
command = QualifyLeadCommand(
    lead_id="lead_123",
    expected_value=50000.0,
    probability=0.6
)
opportunity = await handler.handle(command)
```

### 3. تقدم الفرصة في الخط
```python
command = AdvanceOpportunityStageCommand(
    opportunity_id="opp_456",
    new_stage="negotiation"
)
await handler.handle(command)
```

### 4. إغلاق صفقة
```python
command = CloseOpportunityWonCommand(
    opportunity_id="opp_456",
    won_reason="عرض أفضل من المنافسين"
)
await handler.handle(command)
```

## API Endpoints (قيد التنفيذ)

### Leads
- `POST /api/v1/crm/leads` - إنشاء عميل محتمل
- `GET /api/v1/crm/leads` - قائمة العملاء المحتملين
- `GET /api/v1/crm/leads/{id}` - تفاصيل العميل
- `PATCH /api/v1/crm/leads/{id}` - تحديث
- `POST /api/v1/crm/leads/{id}/contact` - تسجيل تواصل
- `POST /api/v1/crm/leads/{id}/qualify` - تأهيل
- `POST /api/v1/crm/leads/{id}/convert` - تحويل لعميل
- `POST /api/v1/crm/leads/{id}/lose` - فقدان

### Opportunities
- `POST /api/v1/crm/opportunities` - إنشاء فرصة
- `GET /api/v1/crm/opportunities` - قائمة الفرص
- `GET /api/v1/crm/opportunities/{id}` - التفاصيل
- `PATCH /api/v1/crm/opportunities/{id}` - تحديث
- `POST /api/v1/crm/opportunities/{id}/advance` - تقدم للمرحلة التالية
- `POST /api/v1/crm/opportunities/{id}/close-won` - إغلاق مكسوبة
- `POST /api/v1/crm/opportunities/{id}/close-lost` - إغلاق خاسرة

### Activities
- `POST /api/v1/crm/activities` - إنشاء نشاط
- `GET /api/v1/crm/activities` - قائمة الأنشطة
- `POST /api/v1/crm/activities/{id}/complete` - إكمال

### Tasks
- `POST /api/v1/crm/tasks` - إنشاء مهمة
- `GET /api/v1/crm/tasks` - قائمة المهام
- `POST /api/v1/crm/tasks/{id}/complete` - إكمال المهمة

### Pipeline
- `GET /api/v1/crm/pipeline/analytics` - تحليلات خط الأنابيب
- `GET /api/v1/crm/pipeline/stages` - ملخص المراحل

## الأحداث (Events)

### Lead Events
- `LeadCreatedEvent`
- `LeadContactedEvent`
- `LeadQualifiedEvent`
- `LeadConvertedEvent`
- `LeadLostEvent`

### Opportunity Events
- `OpportunityCreatedEvent`
- `OpportunityStageChangedEvent`
- `OpportunityClosedWonEvent`
- `OpportunityClosedLostEvent`
- `OpportunityQuoteAddedEvent`
- `OpportunityOrderAddedEvent`

## المقاييس والتحليلات

### معدل التحويل (Conversion Rate)
```
Conversion Rate = (Closed Won / Total Closed) × 100
```

### القيمة المرجحة (Weighted Value)
```
Weighted Value = Expected Value × Probability
```

### متوسط دورة المبيعات
```
Avg Sales Cycle = Sum(Days to Close) / Total Deals
```

## الحالة الحالية

✅ Domain Entities - مكتملة  
✅ Domain Events - مكتملة  
✅ Commands - مكتملة  
⏳ Command Handlers - قيد التنفيذ  
⏳ Query Handlers - قيد التنفيذ  
⏳ Database Models - قيد التنفيذ  
⏳ API Routers - قيد التنفيذ  

## الخطوات التالية

1. تنفيذ Command Handlers
2. تنفيذ Query Handlers
3. إنشاء Database Models
4. إنشاء Repository Implementations
5. إنشاء API Schemas و Routers
6. كتابة الاختبارات
7. التوثيق الكامل

## الفريق المطلوب

- مطور Backend: 2-3 أيام
- مطور Frontend: 2-3 أيام
- مختبر: 1 يوم

**الإجمالي**: ~1 أسبوع للتنفيذ الكامل
