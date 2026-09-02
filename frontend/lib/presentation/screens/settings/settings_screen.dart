import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';
import '../../providers/theme_provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  String? _error;
  bool _isSaving = false;
  late TabController _tabCtrl;
  Map<String, dynamic> _allSettings = {};

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 7, vsync: this);
    _loadAllSettings();
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> _currencies = [];

  Future<void> _loadAllSettings() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final response = await _api.getSettings();
      final data = response['data'] ?? response;
      if (data is Map) {
        _allSettings = Map<String, dynamic>.from(data);
        final ui = _allSettings['ui'];
        if (ui is Map) {
          final savedTheme = ui['theme'] ?? 'system';
          await context.read<ThemeProvider>().setMode(savedTheme);
        }
      }
      await CurrencyHelper.load();
      _currencies = CurrencyHelper.currencies;
      setState(() => _isLoading = false);
    } catch (e) {
      setState(() { _error = ErrorUtils.sanitize(e); _isLoading = false; });
    }
  }

  Map<String, dynamic> _section(String key) {
    final s = _allSettings[key];
    return (s is Map) ? Map<String, dynamic>.from(s) : {};
  }

  Future<void> _saveSection(String section, Map<String, dynamic> data) async {
    setState(() => _isSaving = true);
    try {
      await _api.put('/settings', data: {section: data});
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم الحفظ بنجاح'), backgroundColor: AppColors.success));
      await _loadAllSettings();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإعدادات'),
        centerTitle: true,
        actions: [
          if (_isSaving) const Padding(
            padding: EdgeInsets.all(12),
            child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
          ),
        ],
        bottom: TabBar(
          controller: _tabCtrl,
          isScrollable: true,
          tabs: const [
            Tab(icon: Icon(Icons.business), text: 'الشركة'),
            Tab(icon: Icon(Icons.receipt_long), text: 'الفواتير'),
            Tab(icon: Icon(Icons.inventory), text: 'المنتجات والعملاء'),
            Tab(icon: Icon(Icons.palette), text: 'الواجهة'),
            Tab(icon: Icon(Icons.notifications), text: 'الإشعارات'),
            Tab(icon: Icon(Icons.print), text: 'الطباعة والأمان'),
            Tab(icon: Icon(Icons.storage), text: 'النظام'),
          ],
        ),
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [TextButton(onPressed: _loadAllSettings, child: const Text('إعادة المحاولة'))],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(
                  controller: _tabCtrl,
                  children: [
                    _buildCompanyTab(),
                    _buildInvoicingTab(),
                    _buildProductsCustomersTab(),
                    _buildUiTab(),
                    _buildNotificationsTab(),
                    _buildPrintingSecurityTab(),
                    _buildSystemTab(),
                  ],
                ),
          ),
        ],
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 1: الشركة
  // ══════════════════════════════════════════════════════════════
  Widget _buildCompanyTab() {
    final inv = _section('invoicing');
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('معلومات الشركة', Icons.business),
        _fieldRow('اسم الشركة', _allSettings['company_name'] ?? '', (v) => _allSettings['company_name'] = v),
        _fieldRow('العنوان', _allSettings['company_address'] ?? '', (v) => _allSettings['company_address'] = v),
        _fieldRow('الهاتف', _allSettings['company_phone'] ?? '', (v) => _allSettings['company_phone'] = v),
        _fieldRow('البريد الإلكتروني', _allSettings['company_email'] ?? '', (v) => _allSettings['company_email'] = v),
        _fieldRow('الرقم الضريبي', _allSettings['tax_number'] ?? '', (v) => _allSettings['tax_number'] = v),
        const SizedBox(height: 24),
        _sectionHeader('السنة المالية', Icons.calendar_today),
        _dropdownRow('بداية السنة المالية', _allSettings['fiscal_year_start_month']?.toString() ?? '1', {
          '1': 'يناير', '4': 'أبريل', '7': 'يوليو', '10': 'أكتوبر'
        }, (v) => _allSettings['fiscal_year_start_month'] = int.tryParse(v) ?? 1),
        _saveButton('حفظ إعدادات الشركة', () {
          final data = Map<String, dynamic>.from(_allSettings)..remove('ui')..remove('invoicing')..remove('purchasing')..remove('products')..remove('customers')..remove('suppliers')..remove('users')..remove('notifications')..remove('printer')..remove('backup');
          _api.updateSettings(data);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('تم الحفظ بنجاح'), backgroundColor: AppColors.success));
        }),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 2: الفواتير والمشتريات
  // ══════════════════════════════════════════════════════════════
  Widget _buildInvoicingTab() {
    final inv = _section('invoicing');
    final purch = _section('purchasing');
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('إعدادات الفواتير', Icons.receipt_long),
        _dropdownRow('العملة الافتراضية', inv['default_currency'] ?? 'USD', {
          for (final c in _currencies) (c['code'] ?? '').toString(): '${c['code'] ?? ''} - ${c['name'] ?? ''}'
        }, (v) => inv['default_currency'] = v),
        _fieldRow('بادئة الفواتير', inv['invoice_prefix'] ?? 'INV-', (v) => inv['invoice_prefix'] = v),
        _fieldRow('طول رقم الفاتورة', inv['invoice_number_length']?.toString() ?? '6', (v) => inv['invoice_number_length'] = int.tryParse(v) ?? 6),
        _switchRow('توليد تلقائي للأرقام', inv['auto_generate_number'] ?? true, (v) => inv['auto_generate_number'] = v),
        _switchRow('إظهار الضريبة', inv['show_tax'] ?? true, (v) => inv['show_tax'] = v),
        _fieldRow('نسبة الضريبة (%)', inv['default_tax_rate']?.toString() ?? '11', (v) => inv['default_tax_rate'] = double.tryParse(v) ?? 11),
        _switchRow('إجبار اختيار العميل', inv['require_customer'] ?? true, (v) => inv['require_customer'] = v),
        _switchRow('السماح بتعديل المسودات', inv['allow_draft_edit'] ?? true, (v) => inv['allow_draft_edit'] = v),
        _fieldRow('أيام الاستحقاق', inv['days_before_due']?.toString() ?? '30', (v) => inv['days_before_due'] = int.tryParse(v) ?? 30),
        _fieldRow('ملاحظات الفاتورة الافتراضية', inv['invoice_notes_template'] ?? '', (v) => inv['invoice_notes_template'] = v),
        const SizedBox(height: 24),
        _sectionHeader('إعدادات المشتريات', Icons.shopping_cart),
        _fieldRow('بادئة أوامر الشراء', purch['purchase_prefix'] ?? 'PO-', (v) => purch['purchase_prefix'] = v),
        _fieldRow('طول رقم الأمر', purch['purchase_number_length']?.toString() ?? '6', (v) => purch['purchase_number_length'] = int.tryParse(v) ?? 6),
        _switchRow('توليد تلقائي', purch['auto_generate_number'] ?? true, (v) => purch['auto_generate_number'] = v),
        _switchRow('إجبار اختيار المورد', purch['require_supplier'] ?? true, (v) => purch['require_supplier'] = v),
        _switchRow('الاستلام التلقائي عند الترحيل', purch['auto_receive_on_post'] ?? false, (v) => purch['auto_receive_on_post'] = v),
        const SizedBox(height: 24),
        _saveButton('حفظ إعدادات الفواتير والمشتريات', () => _saveSection('invoicing', inv)),
        const SizedBox(height: 8),
        _saveButton('حفظ إعدادات المشتريات', () => _saveSection('purchasing', purch)),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 3: المنتجات والعملاء والموردين
  // ══════════════════════════════════════════════════════════════
  Widget _buildProductsCustomersTab() {
    final prod = _section('products');
    final cust = _section('customers');
    final supp = _section('suppliers');
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('إعدادات المنتجات', Icons.inventory),
        _fieldRow('الحد الأدنى للمخزون', prod['low_stock_threshold']?.toString() ?? '10', (v) => prod['low_stock_threshold'] = int.tryParse(v) ?? 10),
        _switchRow('تتبع الدفعات', prod['enable_batch_tracking'] ?? false, (v) => prod['enable_batch_tracking'] = v),
        _switchRow('تتبع الأرقام التسلسلية', prod['enable_serial_tracking'] ?? false, (v) => prod['enable_serial_tracking'] = v),
        _fieldRow('بادئة كود المنتج', prod['code_prefix'] ?? 'PRD-', (v) => prod['code_prefix'] = v),
        _switchRow('توليد كود تلقائي', prod['auto_generate_code'] ?? true, (v) => prod['auto_generate_code'] = v),
        const SizedBox(height: 24),
        _sectionHeader('إعدادات العملاء', Icons.people),
        _fieldRow('بادئة كود العميل', cust['code_prefix'] ?? 'CUS-', (v) => cust['code_prefix'] = v),
        _switchRow('توليد كود تلقائي', cust['auto_generate_code'] ?? true, (v) => cust['auto_generate_code'] = v),
        _switchRow('إجبار الرقم الضريبي', cust['require_tax_number'] ?? false, (v) => cust['require_tax_number'] = v),
        _switchRow('فحص حد الائتمان', cust['enable_credit_check'] ?? false, (v) => cust['enable_credit_check'] = v),
        const SizedBox(height: 24),
        _sectionHeader('إعدادات الموردين', Icons.local_shipping),
        _fieldRow('بادئة كود المورد', supp['code_prefix'] ?? 'SUP-', (v) => supp['code_prefix'] = v),
        _switchRow('توليد كود تلقائي', supp['auto_generate_code'] ?? true, (v) => supp['auto_generate_code'] = v),
        _switchRow('إجبار الرقم الضريبي', supp['require_tax_number'] ?? false, (v) => supp['require_tax_number'] = v),
        const SizedBox(height: 24),
        _saveButton('حفظ إعدادات المنتجات', () => _saveSection('products', prod)),
        const SizedBox(height: 8),
        _saveButton('حفظ إعدادات العملاء', () => _saveSection('customers', cust)),
        const SizedBox(height: 8),
        _saveButton('حفظ إعدادات الموردين', () => _saveSection('suppliers', supp)),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 4: الواجهة
  // ══════════════════════════════════════════════════════════════
  Widget _buildUiTab() {
    final ui = _section('ui');
    final currentTheme = ui['theme'] ?? 'system';
    final currentLang = ui['language'] ?? 'ar';
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('المظهر', Icons.palette),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            RadioListTile<String>(
              title: const Text('النظام الافتراضي'),
              subtitle: const Text('يتبع إعدادات الجهاز'),
              value: 'system', groupValue: currentTheme,
              onChanged: (v) => _saveSection('ui', {'theme': v}),
              secondary: const Icon(Icons.brightness_auto),
            ),
            RadioListTile<String>(
              title: const Text('الوضع الفاتح'),
              value: 'light', groupValue: currentTheme,
              onChanged: (v) => _saveSection('ui', {'theme': v}),
              secondary: const Icon(Icons.light_mode),
            ),
            RadioListTile<String>(
              title: const Text('الوضع الداكن'),
              value: 'dark', groupValue: currentTheme,
              onChanged: (v) => _saveSection('ui', {'theme': v}),
              secondary: const Icon(Icons.dark_mode),
            ),
          ]),
        ),
        const SizedBox(height: 24),
        _sectionHeader('اللغة', Icons.language),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            RadioListTile<String>(
              title: const Text('العربية'),
              value: 'ar', groupValue: currentLang,
              onChanged: (v) => _saveSection('ui', {'language': v}),
              secondary: const Text('ع', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            ),
            RadioListTile<String>(
              title: const Text('English'),
              value: 'en', groupValue: currentLang,
              onChanged: (v) => _saveSection('ui', {'language': v}),
              secondary: const Text('En', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            ),
          ]),
        ),
        const SizedBox(height: 24),
        _sectionHeader('خيارات إضافية', Icons.tune),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            SwitchListTile(
              title: const Text('التحركات والتأثيرات'),
              subtitle: const Text('تشغيل/إيقاف تحركات الواجهة'),
              value: ui['animations_enabled'] ?? true,
              onChanged: (v) => _saveSection('ui', {'animations_enabled': v}),
              secondary: const Icon(Icons.animation),
            ),
            SwitchListTile(
              title: const Text('تلميحات الأدوات'),
              subtitle: const Text('إظهار تلميحات عند التوقف فوق العناصر'),
              value: ui['show_tooltips'] ?? true,
              onChanged: (v) => _saveSection('ui', {'show_tooltips': v}),
              secondary: const Icon(Icons.lightbulb_outline),
            ),
            SwitchListTile(
              title: const Text('الحفظ التلقائي'),
              subtitle: const Text('حفظ البيانات تلقائياً'),
              value: (ui['auto_save_interval'] ?? 0) > 0,
              onChanged: (v) => _saveSection('ui', {'auto_save_interval': v ? 30 : 0}),
              secondary: const Icon(Icons.save),
            ),
            SwitchListTile(
              title: const Text('شريط الحالة'),
              subtitle: const Text('إظهار شريط الحالة في الأسفل'),
              value: ui['show_status_bar'] ?? true,
              onChanged: (v) => _saveSection('ui', {'show_status_bar': v}),
              secondary: const Icon(Icons.linear_scale),
            ),
            SwitchListTile(
              title: const Text('تقليل الشريط الجانبي'),
              value: ui['sidebar_collapsed'] ?? false,
              onChanged: (v) => _saveSection('ui', {'sidebar_collapsed': v}),
              secondary: const Icon(Icons.menu_open),
            ),
            SwitchListTile(
              title: const Text('تأكيد الإغلاق'),
              subtitle: const Text('الconfirm قبل إغلاق النافذة'),
              value: ui['confirm_before_close'] ?? false,
              onChanged: (v) => _saveSection('ui', {'confirm_before_close': v}),
              secondary: const Icon(Icons.exit_to_app),
            ),
          ]),
        ),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 5: الإشعارات
  // ══════════════════════════════════════════════════════════════
  Widget _buildNotificationsTab() {
    final notif = _section('notifications');
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('إشعارات التطبيق', Icons.notifications),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            SwitchListTile(
              title: const Text('إشعارات البريد الإلكتروني'),
              value: notif['enable_email_notifications'] ?? false,
              onChanged: (v) => _saveSection('notifications', {'enable_email_notifications': v}),
              secondary: const Icon(Icons.email_outlined),
            ),
            SwitchListTile(
              title: const Text('إشعارات الصوت'),
              value: notif['enable_sound_notifications'] ?? true,
              onChanged: (v) => _saveSection('notifications', {'enable_sound_notifications': v}),
              secondary: const Icon(Icons.volume_up),
            ),
            SwitchListTile(
              title: const Text('إشعارات النظام'),
              value: notif['enable_system_notifications'] ?? true,
              onChanged: (v) => _saveSection('notifications', {'enable_system_notifications': v}),
              secondary: const Icon(Icons.notifications_active),
            ),
          ]),
        ),
        const SizedBox(height: 24),
        _sectionHeader('تنبيهات تلقائية', Icons.warning),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            SwitchListTile(
              title: const Text('تنبيه المخزون المنخفض'),
              value: notif['low_stock_alert'] ?? true,
              onChanged: (v) => _saveSection('notifications', {'low_stock_alert': v}),
              secondary: const Icon(Icons.inventory),
            ),
            SwitchListTile(
              title: const Text('تنبيه الفواتير المستحقة'),
              value: notif['overdue_invoice_alert'] ?? true,
              onChanged: (v) => _saveSection('notifications', {'overdue_invoice_alert': v}),
              secondary: const Icon(Icons.schedule),
            ),
            SwitchListTile(
              title: const Text('تنبيه مستخدم جديد'),
              value: notif['new_user_alert'] ?? true,
              onChanged: (v) => _saveSection('notifications', {'new_user_alert': v}),
              secondary: const Icon(Icons.person_add),
            ),
            SwitchListTile(
              title: const Text('تنبيه تحديث النظام'),
              value: notif['system_update_alert'] ?? true,
              onChanged: (v) => _saveSection('notifications', {'system_update_alert': v}),
              secondary: const Icon(Icons.system_update),
            ),
          ]),
        ),
        const SizedBox(height: 24),
        _sectionHeader('إعدادات البريد الإلكتروني', Icons.mail),
        _fieldRow('خادم SMTP', notif['email_smtp_server'] ?? '', (v) => notif['email_smtp_server'] = v),
        _fieldRow('منفذ SMTP', notif['email_smtp_port']?.toString() ?? '587', (v) => notif['email_smtp_port'] = int.tryParse(v) ?? 587),
        _fieldRow('اسم المستخدم', notif['email_username'] ?? '', (v) => notif['email_username'] = v),
        _fieldRow('كلمة المرور', notif['email_password'] ?? '', (v) => notif['email_password'] = v),
        _fieldRow('البريد المرسل', notif['email_from'] ?? '', (v) => notif['email_from'] = v),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 6: الطباعة والأمان
  // ══════════════════════════════════════════════════════════════
  Widget _buildPrintingSecurityTab() {
    final printer = _section('printer');
    final users = _section('users');
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('إعدادات الطباعة', Icons.print),
        _dropdownRow('حجم الورق', printer['paper_size'] ?? 'A4', {
          'A4': 'A4', 'A5': 'A5', 'Letter': 'Letter', 'Legal': 'Legal'
        }, (v) => printer['paper_size'] = v),
        _fieldRow('عدد النسخ', printer['copies']?.toString() ?? '1', (v) => printer['copies'] = int.tryParse(v) ?? 1),
        _switchRow('طباعة على الوجهين', printer['print_duplex'] ?? false, (v) => printer['print_duplex'] = v),
        SwitchListTile(
          title: const Text('إظهار شعار الشركة'),
          value: printer['show_company_logo'] ?? true,
          onChanged: (v) => _saveSection('printer', {'show_company_logo': v}),
          secondary: const Icon(Icons.image),
        ),
        SwitchListTile(
          title: const Text('إظهار معلومات الشركة'),
          value: printer['show_company_info'] ?? true,
          onChanged: (v) => _saveSection('printer', {'show_company_info': v}),
          secondary: const Icon(Icons.business),
        ),
        SwitchListTile(
          title: const Text('إظهار التذييل'),
          value: printer['show_footer'] ?? true,
          onChanged: (v) => _saveSection('printer', {'show_footer': v}),
          secondary: const Icon(Icons.format_align_center),
        ),
        _fieldRow('نص التذييل', printer['footer_text'] ?? '', (v) => printer['footer_text'] = v),
        const SizedBox(height: 24),
        _sectionHeader('إعدادات الأمان', Icons.security),
        SwitchListTile(
          title: const Text('كلمة مرور قوية'),
          subtitle: const Text('إجبار الأحرف والأرقام والرموز'),
          value: users['require_strong_password'] ?? true,
          onChanged: (v) => _saveSection('users', {'require_strong_password': v}),
          secondary: const Icon(Icons.lock),
        ),
        _fieldRow('الحد الأدنى لكلمة المرور', users['password_min_length']?.toString() ?? '8', (v) => _saveSection('users', {'password_min_length': int.tryParse(v) ?? 8})),
        _fieldRow('مهلة الجلسة (دقيقة)', users['session_timeout_minutes']?.toString() ?? '60', (v) => _saveSection('users', {'session_timeout_minutes': int.tryParse(v) ?? 60})),
        _fieldRow('الحد الأقصى لمحاولات الدخول', users['max_login_attempts']?.toString() ?? '5', (v) => _saveSection('users', {'max_login_attempts': int.tryParse(v) ?? 5})),
        _fieldRow('دقائق القفل', users['lockout_minutes']?.toString() ?? '15', (v) => _saveSection('users', {'lockout_minutes': int.tryParse(v) ?? 15})),
        SwitchListTile(
          title: const Text('تسجيل التدقيق'),
          value: users['audit_log_enabled'] ?? true,
          onChanged: (v) => _saveSection('users', {'audit_log_enabled': v}),
          secondary: const Icon(Icons.history),
        ),
        const SizedBox(height: 24),
        _saveButton('حفظ إعدادات الطباعة', () => _saveSection('printer', printer)),
        const SizedBox(height: 8),
        _saveButton('حفظ إعدادات الأمان', () => _saveSection('users', users)),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // TAB 7: النظام
  // ══════════════════════════════════════════════════════════════
  Widget _buildSystemTab() {
    final backup = _section('backup');
    return ListView(
      padding: const EdgeInsets.all(AppDimens.s3),
      children: [
        _sectionHeader('النسخ الاحتياطي', Icons.backup),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            SwitchListTile(
              title: const Text('نسخ احتياطي تلقائي'),
              value: backup['auto_backup_enabled'] ?? false,
              onChanged: (v) => _saveSection('backup', {'auto_backup_enabled': v}),
              secondary: const Icon(Icons.backup),
            ),
            _fieldRow('الفاصل بالساعات', backup['backup_interval_hours']?.toString() ?? '24', (v) => _saveSection('backup', {'backup_interval_hours': int.tryParse(v) ?? 24})),
            _fieldRow('أيام الاحتفاظ', backup['backup_retention_days']?.toString() ?? '30', (v) => _saveSection('backup', {'backup_retention_days': int.tryParse(v) ?? 30})),
            SwitchListTile(
              title: const Text('تضمين المرفقات'),
              value: backup['include_attachments'] ?? true,
              onChanged: (v) => _saveSection('backup', {'include_attachments': v}),
              secondary: const Icon(Icons.attach_file),
            ),
            SwitchListTile(
              title: const Text('ضغط النسخة'),
              value: backup['compress_backup'] ?? true,
              onChanged: (v) => _saveSection('backup', {'compress_backup': v}),
              secondary: const Icon(Icons.archive),
            ),
            SwitchListTile(
              title: const Text('تشفير النسخة'),
              value: backup['encrypt_backup'] ?? false,
              onChanged: (v) => _saveSection('backup', {'encrypt_backup': v}),
              secondary: const Icon(Icons.enhanced_encryption),
            ),
          ]),
        ),
        const SizedBox(height: 24),
        _sectionHeader('معلومات النظام', Icons.info),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            const ListTile(leading: Icon(Icons.storage), title: Text('قاعدة البيانات'), trailing: Text('PostgreSQL')),
            const Divider(),
            const ListTile(leading: Icon(Icons.code), title: Text('إطار العمل'), trailing: Text('FastAPI + Flutter')),
            const Divider(),
            const ListTile(leading: Icon(Icons.desktop_windows), title: Text('المنصة'), trailing: Text('Windows Desktop')),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('إصدار النظام'),
              trailing: Text(_allSettings['version']?.toString() ?? '3.0.0'),
            ),
          ]),
        ),
        const SizedBox(height: 24),
        _sectionHeader('حول التطبيق', Icons.help_outline),
        AppCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            const ListTile(leading: Icon(Icons.flutter_dash), title: Text('واجهة المستخدم'), trailing: Text('Flutter')),
            const Divider(),
            const ListTile(leading: Icon(Icons.api), title: Text('واجهة البرمجة'), trailing: Text('FastAPI')),
            const Divider(),
            const ListTile(leading: Icon(Icons.gavel), title: Text('الترخيص'), trailing: Text('MIT License')),
            const Divider(),
            Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text('© 2026 YAseen ERP. جميع الحقوق محفوظة.',
                  style: TextStyle(color: AppColors.textHint, fontSize: 12)),
              ),
            ),
          ]),
        ),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════
  // أدوات مساعدة
  // ══════════════════════════════════════════════════════════════
  Widget _sectionHeader(String title, IconData icon) {
    return Row(children: [
      Icon(icon, size: 20, color: AppColors.primary),
      const SizedBox(width: AppDimens.s2),
      Text(title, style: AppTextStyles.titleMedium),
    ]);
  }

  Widget _fieldRow(String label, String value, Function(String) onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: TextFormField(
        initialValue: value,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
          isDense: true,
        ),
        onChanged: onChanged,
      ),
    );
  }

  Widget _dropdownRow(String label, String value, Map<String, String> items, Function(String) onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: DropdownButtonFormField<String>(
        value: items.containsKey(value) ? value : items.keys.first,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
        items: items.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
        onChanged: (v) { if (v != null) onChanged(v); },
      ),
    );
  }

  Widget _switchRow(String title, bool value, Function(bool) onChanged) {
    return SwitchListTile(
      title: Text(title),
      value: value,
      onChanged: onChanged,
    );
  }

  Widget _saveButton(String label, VoidCallback onPressed) {
    return AppButton(
      label: label,
      icon: Icons.save,
      variant: AppButtonVariant.success,
      loading: _isSaving,
      expanded: true,
      onPressed: onPressed,
    );
  }
}
