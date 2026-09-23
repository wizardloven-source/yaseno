// C:\Users\MTC\yaseeno\frontend\lib\presentation\widgets\sidebar_widget.dart

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimensions.dart';
import '../../theme/app_text_styles.dart';
import '../providers/auth_provider.dart';

/// عنصر قائمة جانبية داخل قسم ضعيف (collapsible section).
class _SidebarItem {
  final IconData icon;
  final String label;
  final String route;
  final List<String>? permission;

  const _SidebarItem(this.icon, this.label, this.route, [this.permission]);
}

class SidebarWidget extends StatelessWidget {
  final String currentRoute;

  const SidebarWidget({
    super.key,
    required this.currentRoute,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: AppDimens.sidebarWidth,
      color: isDark ? const Color(0xFF17191E) : AppColors.sidebarBackground,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF17191E) : AppColors.sidebarBackground,
        boxShadow: [
          BoxShadow(
            color: const Color(0x14000000),
            blurRadius: 12,
            offset: const Offset(2, 0),
          ),
        ],
      ),
      child: Column(
        children: [
          // ============================================================
          // Header - الشعار والاسم
          // ============================================================
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.primaryDark, AppColors.primary],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(16),
                bottomRight: Radius.circular(16),
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.account_balance,
                    size: 28,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'YAseen ERP',
                      style: AppTextStyles.titleLarge.copyWith(
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      'نظام محاسبي متكامل',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: Colors.white70,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 8),

          // ============================================================
          // قائمة المستخدم
          // ============================================================
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF23262D) : AppColors.sidebarSelected,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: isDark ? scheme.outlineVariant : AppColors.primaryContainer,
                ),
              ),
              child: Row(
                children: [
                  const CircleAvatar(
                    radius: 18,
                    backgroundColor: Colors.blue,
                    child: Icon(
                      Icons.person,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Consumer<AuthProvider>(
                          builder: (context, auth, _) => Text(
                            auth?.username ?? 'مدير النظام',
                            style: AppTextStyles.labelLarge,
                          ),
                        ),
                        Consumer<AuthProvider>(
                          builder: (context, auth, _) => Text(
                            auth?.user?['email'] ?? '',
                            style: AppTextStyles.bodySmall.copyWith(
                              color: AppColors.sidebarIcon,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: Icon(
                      Icons.logout,
                      size: 20,
                      color: AppColors.textSecondary,
                    ),
                    onPressed: () {
                      _showLogoutDialog(context);
                    },
                    tooltip: 'تسجيل الخروج',
                  ),
                ],
              ),
            ),
          ),

          const Divider(height: 4),

          // ============================================================
          // قائمة العناصر الرئيسية (أقسام قابلة للطي)
          // ============================================================
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 4),
              children: [
                _buildMenuItem(
                  context,
                  icon: Icons.dashboard,
                  label: 'لوحة التحكم',
                  route: '/',
                  isSelected: currentRoute == '/',
                ),

                // ---- المحاسبة ----
                _buildCollapsibleSection(
                  context,
                  title: 'المحاسبة',
                  icon: Icons.receipt_long,
                  items: [
                    if (_canShow(context, ['post_entry', 'create_entry']))
                      const _SidebarItem(
                          Icons.receipt_long, 'قيود اليومية', '/journal-entries'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.account_tree, 'دفتر الأستاذ', '/general-ledger'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.list_alt, 'دليل الحسابات', '/chart-of-accounts'),
                    if (_canShow(context, ['post_entry', 'open_period', 'close_period']))
                      const _SidebarItem(
                          Icons.calendar_month, 'الفترات المالية', '/fiscal-periods'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.menu_book, 'الأرصدة الافتتاحية', '/opening-balances'),
                  ],
                ),

                // ---- المبيعات والمشتريات ----
                _buildCollapsibleSection(
                  context,
                  title: 'المبيعات والمشتريات',
                  icon: Icons.storefront,
                  items: const [
                    _SidebarItem(Icons.people, 'العملاء', '/customers'),
                    _SidebarItem(Icons.business, 'الموردين', '/suppliers'),
                    _SidebarItem(Icons.inventory_2, 'المنتجات', '/products'),
                    _SidebarItem(Icons.receipt, 'الفواتير', '/invoices'),
                    _SidebarItem(
                        Icons.replay, 'مرتجع المبيعات', '/returns/sales'),
                    _SidebarItem(
                        Icons.replay_circle_filled, 'مرتجع المشتريات', '/returns/purchases'),
                    _SidebarItem(Icons.shopping_cart, 'المشتريات', '/purchase-orders'),
                    _SidebarItem(Icons.request_quote, 'عروض الأسعار', '/sales/quotes'),
                    _SidebarItem(Icons.shopping_bag, 'أوامر البيع', '/sales/orders'),
                    _SidebarItem(Icons.delivery_dining, 'إشعارات التسليم', '/sales/deliveries'),
                    _SidebarItem(Icons.inventory_2, 'قوائم الانتقاء', '/sales/picking'),
                    _SidebarItem(Icons.local_shipping, 'لوحة الشحن', '/sales/shipping'),
                  ],
                ),

                // ---- المشاريع ----
                if (_canShow(context, ['system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.construction,
                    label: 'المشاريع',
                    route: '/projects',
                    isSelected: currentRoute == '/projects' ||
                        currentRoute.startsWith('/projects/'),
                  ),

                // ---- نقطة البيع (قسم مؤطَّر) ----
                _buildPosSection(context),

                // ---- الصناديق والدفعات ----
                _buildCollapsibleSection(
                  context,
                  title: 'الصناديق والدفعات',
                  icon: Icons.account_balance_wallet,
                  items: const [
                    _SidebarItem(Icons.account_balance_wallet, 'الصناديق', '/funds'),
                    _SidebarItem(Icons.payments, 'الدفعات', '/payments'),
                  ],
                ),

                // ---- المخزون والأصول ----
                _buildCollapsibleSection(
                  context,
                  title: 'المخزون والأصول',
                  icon: Icons.warehouse,
                  items: [
                    const _SidebarItem(Icons.warehouse, 'إدارة المخزون', '/inventory'),
                    if (_canShow(context, ['system_config', 'post_entry']))
                      const _SidebarItem(Icons.apartment, 'الأصول الثابتة', '/assets'),
                  ],
                ),

                // ---- الإعدادات ----
                _buildCollapsibleSection(
                  context,
                  title: 'الإعدادات',
                  icon: Icons.settings,
                  items: [
                    if (_canShow(context, ['system_config']))
                      const _SidebarItem(Icons.currency_exchange, 'العملات', '/currencies'),
                    if (_canShow(context, ['system_config']))
                      const _SidebarItem(Icons.location_on, 'المواقع', '/sites'),
                    if (_canShow(context, ['system_config']))
                      const _SidebarItem(Icons.account_balance, 'مراكز التكلفة', '/centers'),
                    if (_canShow(context, ['system_config']))
                      const _SidebarItem(Icons.store, 'فروع العملاء', '/branches'),
                    if (_canShow(context, ['system_config']))
                      const _SidebarItem(Icons.upload_file, 'مركز الاستيراد', '/import-center'),
                  ],
                ),

                // ---- سير العمل والإشعارات ----
                _buildCollapsibleSection(
                  context,
                  title: 'سير العمل والإشعارات',
                  icon: Icons.approval,
                  items: [
                    if (_canShow(context, ['create_draft', 'system_config']))
                      const _SidebarItem(
                          Icons.account_tree, 'تعريف سير العمل', '/workflows'),
                    if (_canShow(context, ['create_draft']))
                      const _SidebarItem(Icons.approval, 'الاعتمادات', '/approvals'),
                    const _SidebarItem(Icons.notifications, 'الإشعارات', '/notifications'),
                  ],
                ),

                // ---- التقارير ----
                _buildCollapsibleSection(
                  context,
                  title: 'التقارير',
                  icon: Icons.pie_chart,
                  items: [
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.account_balance, 'ميزان المراجعة', '/reports/trial-balance'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.trending_up, 'قائمة الدخل', '/reports/income-statement'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.pie_chart, 'الميزانية العمومية', '/reports/balance-sheet'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.payments, 'التدفقات النقدية', '/reports/cash-flow'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.hourglass_empty, 'تقادم الذمم', '/reports/aging'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.compare_arrows, 'المطابقة البنكية', '/reports/reconciliation'),
                    if (_canShow(context, ['post_entry', 'manage_accounts']))
                      const _SidebarItem(
                          Icons.donut_large, 'الموازنات', '/reports/budgets'),
                  ],
                ),

                // ---- النظام ----
                _buildCollapsibleSection(
                  context,
                  title: 'النظام',
                  icon: Icons.admin_panel_settings,
                  items: [
                    if (_canShow(context, ['manage_users']))
                      const _SidebarItem(Icons.group, 'المستخدمين', '/users'),
                    if (_canShow(context, ['manage_users']))
                      const _SidebarItem(Icons.security, 'الأدوار والصلاحيات', '/roles'),
                    if (_canShow(context, ['manage_users']))
                      const _SidebarItem(Icons.history, 'سجل التدقيق', '/audit'),
                    const _SidebarItem(Icons.person, 'الملف الشخصي', '/profile'),
                    if (_canShow(context, ['system_config']))
                      const _SidebarItem(Icons.settings, 'الإعدادات', '/settings'),
                  ],
                ),
              ],
            ),
          ),

          // ============================================================
          // Footer - معلومات الإصدار
          // ============================================================
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: isDark ? const Color(0xFF1C1C1E) : AppColors.sidebarDivider),
              ),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1A3A5C) : AppColors.primaryContainer,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'v3.0.0',
                        style: AppTextStyles.labelSmall.copyWith(
                          color: isDark ? DarkText.primary : AppColors.primary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'YAseen ERP © 2026',
                      style: AppTextStyles.labelSmall.copyWith(
                        color: isDark ? DarkText.textLight : AppColors.sidebarSectionHeader,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  'جميع الحقوق محفوظة',
                  style: AppTextStyles.labelSmall.copyWith(
                    color: isDark ? DarkText.hint : AppColors.textHint,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // دوال مساعدة
  // ============================================================

  // القائمة الجانبية تُبسط لكل أنواع الشركات (§2.3 Modular):
  // - المؤسسات (is_admin / من يملك صلاحية واسعة) ترى كل الأقسام المتقدمة.
  // - الدكان الصغير يرى فقط الأقسام المصرّح بها (مبيعات، عملاء، مخزون، نقد).
  bool _canShow(BuildContext context, List<String> required) {
    final auth = context.watch<AuthProvider>();
    if (auth.isSuperAdmin) return true;
    if (auth.hasPermission('manage_users')) return true;
    if (required.isEmpty) return true;
    return auth.hasAnyPermission(required);
  }

  /// قسم قابل للطي: يفتح تلقائياً عند التنقّل داخل إحدى روابطه.
  Widget _buildCollapsibleSection(
    BuildContext context, {
    required String title,
    required IconData icon,
    required List<_SidebarItem> items,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final anyVisible = items.isNotEmpty;
    if (!anyVisible) return const SizedBox.shrink();

    final selectedItem = items
        .where((it) =>
            currentRoute == it.route ||
            (it.route != '/' && currentRoute.startsWith(it.route)))
        .toList();
    final isOpen = selectedItem.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(height: 4),
        Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            tilePadding: const EdgeInsets.symmetric(horizontal: 16),
            childrenPadding: const EdgeInsets.only(bottom: 4),
            initiallyExpanded: isOpen,
            leading: Icon(
              icon,
              size: 22,
              color: isOpen
                  ? AppColors.sidebarIconSelected
                  : (isDark ? Colors.white54 : AppColors.sidebarIcon),
            ),
            title: Text(
              title,
              style: AppTextStyles.sectionHeader.copyWith(
                color: isOpen
                    ? (isDark ? Colors.white : AppColors.primary)
                    : (isDark ? DarkText.hint : AppColors.sidebarSectionHeader),
              ),
            ),
            iconColor: isDark ? Colors.white54 : AppColors.sidebarIcon,
            collapsedIconColor: isDark ? Colors.white54 : AppColors.sidebarIcon,
            shape: const Border(),
            collapsedShape: const Border(),
            children: [
              for (final item in items)
                _buildMenuItem(
                  context,
                  icon: item.icon,
                  label: item.label,
                  route: item.route,
                  isSelected: currentRoute == item.route ||
                      (item.route != '/' &&
                          currentRoute.startsWith(item.route)),
                ),
            ],
          ),
        ),
      ],
    );
  }

  /// قسم «نقطة البيع» مع تمييز بصري (حدود + خلفية متدرجة) ليكون بارزاً ومستقراً.
  Widget _buildPosSection(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isMain = currentRoute == '/pos';
    final isReceipts = currentRoute.startsWith('/pos/receipts');
    final isOpen = isMain || isReceipts;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark ? const Color(0xFF2E4A70) : AppColors.primaryContainer,
        ),
        gradient: LinearGradient(
          colors: isDark
              ? [const Color(0xFF1B2A44), isDark ? const Color(0xFF17191E) : AppColors.sidebarBackground]
              : [
                  AppColors.primaryContainer.withValues(alpha: 0.30),
                  Colors.transparent,
                ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
          childrenPadding: const EdgeInsets.only(bottom: 4),
          initiallyExpanded: isOpen,
          leading: Icon(
            Icons.point_of_sale,
            size: 22,
            color: isOpen
                ? AppColors.sidebarIconSelected
                : isDark
                    ? Colors.white54
                    : AppColors.sidebarIcon,
          ),
          title: Text(
            'نقطة البيع',
            style: AppTextStyles.sectionHeader.copyWith(
              color: isOpen
                  ? (isDark ? Colors.white : AppColors.primary)
                  : (isDark ? DarkText.hint : AppColors.sidebarSectionHeader),
            ),
          ),
          iconColor: isDark ? Colors.white54 : AppColors.sidebarIcon,
          collapsedIconColor: isDark ? Colors.white54 : AppColors.sidebarIcon,
          shape: const Border(),
          collapsedShape: const Border(),
          children: [
            _buildMenuItem(
              context,
              icon: Icons.shopping_cart,
              label: 'الشاشة الرئيسية',
              route: '/pos',
              isSelected: isMain,
            ),
            _buildMenuItem(
              context,
              icon: Icons.receipt_long,
              label: 'إيصالات نقطة البيع',
              route: '/pos/receipts',
              isSelected: isReceipts,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMenuItem(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String route,
    bool isSelected = false,
    bool enabled = true,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final Color iconColor = isSelected
        ? AppColors.sidebarIconSelected
        : enabled
            ? (isDark ? Colors.white54 : AppColors.sidebarIcon)
            : AppColors.textHint;
    final Color textColor = isSelected
        ? (isDark ? Colors.white : AppColors.primary)
        : enabled
            ? (isDark ? Colors.white70 : AppColors.sidebarText)
            : AppColors.textHint;
    return ListTile(
      leading: Icon(icon, color: iconColor, size: 22),
      title: Text(
        label,
        style: (isSelected ? AppTextStyles.navItemSelected : AppTextStyles.navItem)
            .copyWith(color: textColor),
      ),
      trailing: isSelected
          ? Container(
              width: 4,
              height: 24,
              decoration: BoxDecoration(
                color: AppColors.sidebarIconSelected,
                borderRadius: BorderRadius.circular(2),
              ),
            )
          : null,
      selected: isSelected,
      selectedTileColor: isDark ? const Color(0xFF23262D) : AppColors.sidebarSelected,
      enabled: enabled,
      onTap: enabled
          ? () {
              if (route != currentRoute) {
                context.go(route);
              }
            }
          : null,
      hoverColor: isDark ? const Color(0xFF23262D) : AppColors.sidebarSelected,
      splashColor: AppColors.primaryContainer,
    );
  }

  void _showLogoutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تسجيل الخروج'),
        content: const Text('هل أنت متأكد من رغبتك في تسجيل الخروج؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              final auth = context.read<AuthProvider>();
              await auth.logout();
              if (context.mounted) context.go('/login');
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
              foregroundColor: Colors.white,
            ),
            child: const Text('تسجيل الخروج'),
          ),
        ],
      ),
    );
  }
}