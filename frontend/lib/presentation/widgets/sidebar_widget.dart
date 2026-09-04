// C:\Users\MTC\yaseeno\frontend\lib\presentation\widgets\sidebar_widget.dart

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimensions.dart';
import '../../theme/app_text_styles.dart';
import '../providers/auth_provider.dart';

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
          // قائمة العناصر الرئيسية
          // ============================================================
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 4),
              children: [
                // ---- Dashboard ----
                _buildMenuItem(
                  context,
                  icon: Icons.dashboard,
                  label: 'لوحة التحكم',
                  route: '/',
                  isSelected: currentRoute == '/',
                ),

                const Divider(height: 4),

                // ---- المحاسبة ----
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildSectionHeader('المحاسبة', context),
                if (_canShow(context, ['post_entry', 'create_entry']))
                  _buildMenuItem(
                    context,
                    icon: Icons.receipt_long,
                    label: 'قيود اليومية',
                    route: '/journal-entries',
                    isSelected: currentRoute.startsWith('/journal-entries'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.account_tree,
                    label: 'دفتر الأستاذ',
                    route: '/general-ledger',
                    isSelected: currentRoute == '/general-ledger',
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.list_alt,
                    label: 'دليل الحسابات',
                    route: '/chart-of-accounts',
                    isSelected: currentRoute == '/chart-of-accounts',
                  ),
                if (_canShow(context, ['post_entry', 'open_period', 'close_period']))
                  _buildMenuItem(
                    context,
                    icon: Icons.calendar_month,
                    label: 'الفترات المالية',
                    route: '/fiscal-periods',
                    isSelected: currentRoute == '/fiscal-periods',
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.menu_book,
                    label: 'الأرصدة الافتتاحية',
                    route: '/opening-balances',
                    isSelected: currentRoute == '/opening-balances',
                  ),

                const Divider(height: 4),

                // ---- المبيعات والمشتريات ----
                _buildSectionHeader('المبيعات والمشتريات', context),
                _buildMenuItem(
                  context,
                  icon: Icons.people,
                  label: 'العملاء',
                  route: '/customers',
                  isSelected: currentRoute.startsWith('/customers'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.business,
                  label: 'الموردين',
                  route: '/suppliers',
                  isSelected: currentRoute.startsWith('/suppliers'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.inventory_2,
                  label: 'المنتجات',
                  route: '/products',
                  isSelected: currentRoute.startsWith('/products'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.receipt,
                  label: 'الفواتير',
                  route: '/invoices',
                  isSelected: currentRoute.startsWith('/invoices'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.replay,
                  label: 'مرتجع المبيعات',
                  route: '/returns/sales',
                  isSelected: currentRoute.startsWith('/returns/sales'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.replay_circle_filled,
                  label: 'مرتجع المشتريات',
                  route: '/returns/purchases',
                  isSelected: currentRoute.startsWith('/returns/purchases'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.shopping_cart,
                  label: 'المشتريات',
                  route: '/purchase-orders',
                  isSelected: currentRoute.startsWith('/purchase-orders'),
                ),

                const Divider(height: 4),

                // ---- الصناديق والدفعات ----
                _buildSectionHeader('الصناديق والدفعات', context),
                _buildMenuItem(
                  context,
                  icon: Icons.account_balance_wallet,
                  label: 'الصناديق',
                  route: '/funds',
                  isSelected: currentRoute.startsWith('/funds'),
                ),
                _buildMenuItem(
                  context,
                  icon: Icons.payments,
                  label: 'الدفعات',
                  route: '/payments',
                  isSelected: currentRoute.startsWith('/payments'),
                ),

                const Divider(height: 4),

                // ---- المخزون والأصول ----
                _buildSectionHeader('المخزون والأصول', context),
                _buildMenuItem(
                  context,
                  icon: Icons.warehouse,
                  label: 'إدارة المخزون',
                  route: '/inventory',
                  isSelected: currentRoute == '/inventory',
                ),
                if (_canShow(context, ['system_config', 'post_entry']))
                  _buildMenuItem(
                    context,
                    icon: Icons.apartment,
                    label: 'الأصول الثابتة',
                    route: '/assets',
                    isSelected: currentRoute == '/assets',
                  ),

                const Divider(height: 4),

                // ---- الإعدادات ----
                if (_canShow(context, ['system_config']))
                  _buildSectionHeader('الإعدادات', context),
                if (_canShow(context, ['system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.currency_exchange,
                    label: 'العملات',
                    route: '/currencies',
                    isSelected: currentRoute == '/currencies',
                  ),
                if (_canShow(context, ['system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.location_on,
                    label: 'المواقع',
                    route: '/sites',
                    isSelected: currentRoute == '/sites',
                  ),
                if (_canShow(context, ['system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.account_balance,
                    label: 'مراكز التكلفة',
                    route: '/centers',
                    isSelected: currentRoute == '/centers',
                  ),
                if (_canShow(context, ['system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.store,
                    label: 'فروع العملاء',
                    route: '/branches',
                    isSelected: currentRoute == '/branches',
                  ),

                const Divider(height: 4),

                // ---- سير العمل والإشعارات ----
                if (_canShow(context, ['create_draft', 'system_config']))
                  _buildSectionHeader('سير العمل والإشعارات', context),
                if (_canShow(context, ['create_draft', 'system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.account_tree,
                    label: 'تعريف سير العمل',
                    route: '/workflows',
                    isSelected: currentRoute.startsWith('/workflows'),
                  ),
                if (_canShow(context, ['create_draft']))
                  _buildMenuItem(
                    context,
                    icon: Icons.approval,
                    label: 'الاعتمادات',
                    route: '/approvals',
                    isSelected: currentRoute.startsWith('/approvals'),
                  ),
                _buildMenuItem(
                  context,
                  icon: Icons.notifications,
                  label: 'الإشعارات',
                  route: '/notifications',
                  isSelected: currentRoute.startsWith('/notifications'),
                ),

                const Divider(height: 4),

                // ---- التقارير ----
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildSectionHeader('التقارير', context),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.account_balance,
                    label: 'ميزان المراجعة',
                    route: '/reports/trial-balance',
                    isSelected: currentRoute.startsWith('/reports/trial-balance'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.trending_up,
                    label: 'قائمة الدخل',
                    route: '/reports/income-statement',
                    isSelected: currentRoute.startsWith('/reports/income-statement'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.pie_chart,
                    label: 'الميزانية العمومية',
                    route: '/reports/balance-sheet',
                    isSelected: currentRoute.startsWith('/reports/balance-sheet'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.payments,
                    label: 'التدفقات النقدية',
                    route: '/reports/cash-flow',
                    isSelected: currentRoute.startsWith('/reports/cash-flow'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.hourglass_empty,
                    label: 'تقادم الذمم',
                    route: '/reports/aging',
                    isSelected: currentRoute.startsWith('/reports/aging'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.compare_arrows,
                    label: 'المطابقة البنكية',
                    route: '/reports/reconciliation',
                    isSelected: currentRoute.startsWith('/reports/reconciliation'),
                  ),
                if (_canShow(context, ['post_entry', 'manage_accounts']))
                  _buildMenuItem(
                    context,
                    icon: Icons.donut_large,
                    label: 'الموازنات',
                    route: '/reports/budgets',
                    isSelected: currentRoute.startsWith('/reports/budgets'),
                  ),

                const Divider(height: 4),

                // ---- النظام ----
                if (_canShow(context, ['manage_users']))
                  _buildSectionHeader('النظام', context),
                if (_canShow(context, ['manage_users']))
                  _buildMenuItem(
                    context,
                    icon: Icons.group,
                    label: 'المستخدمين',
                    route: '/users',
                    isSelected: currentRoute.startsWith('/users'),
                  ),
                if (_canShow(context, ['manage_users']))
                  _buildMenuItem(
                    context,
                    icon: Icons.security,
                    label: 'الأدوار والصلاحيات',
                    route: '/roles',
                    isSelected: currentRoute.startsWith('/roles'),
                  ),
                if (_canShow(context, ['manage_users']))
                  _buildMenuItem(
                    context,
                    icon: Icons.history,
                    label: 'سجل التدقيق',
                    route: '/audit',
                    isSelected: currentRoute.startsWith('/audit'),
                  ),
                _buildMenuItem(
                  context,
                  icon: Icons.person,
                  label: 'الملف الشخصي',
                  route: '/profile',
                  isSelected: currentRoute == '/profile',
                ),
                if (_canShow(context, ['system_config']))
                  _buildMenuItem(
                    context,
                    icon: Icons.settings,
                    label: 'الإعدادات',
                    route: '/settings',
                    isSelected: currentRoute.startsWith('/settings'),
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

  Widget _buildSectionHeader(String title, BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Text(
        title,
        style: AppTextStyles.sectionHeader.copyWith(
          color: isDark ? DarkText.hint : AppColors.sidebarSectionHeader,
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