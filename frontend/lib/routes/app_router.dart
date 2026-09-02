import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ya_seen_erp_flutter/services/api_client.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/auth/splash_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/auth/login_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/dashboard/dashboard_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/customers/customer_statement_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/suppliers/supplier_statement_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/funds/fund_detail_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/opening_balances_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/reports/aging_report_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/reports/reconciliation_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/reports/budgets_screen.dart';

// ============================================================
// المحاسبة (Accounting)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/journal_entry_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/create_journal_entry_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/journal_entry_detail_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/chart_of_accounts_screen.dart';

// ============================================================
// العملاء (Customers)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/customers/customers_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/customers/customer_form_screen.dart';

// ============================================================
// الموردين (Suppliers)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/suppliers/suppliers_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/suppliers/supplier_form_screen.dart';

// ============================================================
// المنتجات (Products)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/products/products_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/products/product_form_screen.dart';

// ============================================================
// الفواتير (Invoicing)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/invoicing/invoice_create_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/invoicing/invoice_detail_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/invoicing/invoice_list_screen.dart';

// ============================================================
// الصناديق (Funds)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/funds/fund_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/funds/fund_form_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/funds/fund_transfer_screen.dart';

// ============================================================
// المشتريات (Purchasing)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/purchasing/purchase_order_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/purchasing/purchase_order_form_screen.dart';

// ============================================================
// الدفعات (Payments)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/payments/payment_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/payments/payment_form_screen.dart';

// ============================================================
// المستخدمين (Users)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/users/users_list_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/users/user_form_screen.dart';

// ============================================================
// التقارير (Reports)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/reports/trial_balance_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/reports/income_statement_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/reports/balance_sheet_screen.dart';

// ============================================================
// سير العمل والاعتمادات (Workflows & Approvals)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/workflows/workflows_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/workflows/approvals_screen.dart';

// ============================================================
// الإشعارات (Notifications)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/notifications/notifications_screen.dart';

// ============================================================
// سجل التدقيق (Audit)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/audit/audit_screen.dart';

// ============================================================
// الإعدادات (Settings)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/settings/settings_screen.dart';

// ============================================================
// العملات والمواقع (Currencies, Sites, Centers)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/currencies/currencies_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/sites/sites_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/centers/centers_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/branches/branches_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/roles/roles_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/widgets/main_shell.dart';

// ============================================================
// الأصول الثابتة والمخزون (Assets & Inventory)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/assets/assets_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/inventory/inventory_screen.dart';

// ============================================================
// المحاسبة الإضافية (Additional Accounting)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/fiscal_periods_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/account_form_screen.dart';
import 'package:ya_seen_erp_flutter/presentation/screens/accounting/general_ledger_screen.dart';

// ============================================================
// التقارير الإضافية (Additional Reports)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/reports/cash_flow_screen.dart';

// ============================================================
// الملف الشخصي (Profile)
// ============================================================
import 'package:ya_seen_erp_flutter/presentation/screens/auth/profile_screen.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      final isLoggedIn = ApiClient().isAuthenticated;
      final location = state.matchedLocation;
      if (location == '/splash') return null;
      final isLoginRoute = location == '/login';
      if (!isLoggedIn && !isLoginRoute) return '/login';
      if (isLoggedIn && isLoginRoute) return '/';
      return null;
    },
    routes: [
      // ============================================================
      // شاشة البداية (Splash) - بدون sidebar
      // ============================================================
      GoRoute(
        path: '/splash',
        name: 'splash',
        builder: (context, state) => const SplashScreen(),
      ),

      // ============================================================
      // المصادقة (Authentication) - بدون sidebar
      // ============================================================
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),

      // ============================================================
      // كل الصفحات الأخرى مع Sidebar
      // ============================================================
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          // لوحة التحكم (Dashboard)
          GoRoute(
            path: '/',
            name: 'dashboard',
            builder: (context, state) => const DashboardScreen(),
          ),

          // المحاسبة (Accounting)
          GoRoute(
            path: '/journal-entries',
            name: 'journal_entries',
            builder: (context, state) => const JournalEntryListScreen(),
          ),
          GoRoute(
            path: '/journal-entries/create',
            name: 'create_journal_entry',
            builder: (context, state) => const CreateJournalEntryScreen(),
          ),
          GoRoute(
            path: '/journal-entries/:id',
            name: 'journal_entry_detail',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return JournalEntryDetailScreen(entryId: id);
            },
          ),
          GoRoute(
            path: '/chart-of-accounts',
            name: 'chart_of_accounts',
            builder: (context, state) => const ChartOfAccountsScreen(),
          ),

          // العملاء (Customers)
          GoRoute(
            path: '/customers',
            name: 'customers',
            builder: (context, state) => const CustomersListScreen(),
          ),
          GoRoute(
            path: '/customers/create',
            name: 'create_customer',
            builder: (context, state) => const CustomerFormScreen(),
          ),
          GoRoute(
            path: '/customers/:id',
            name: 'edit_customer',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return CustomerFormScreen(customerId: id);
            },
          ),
          GoRoute(
            path: '/customers/:id/statement',
            name: 'customer_statement',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              final name = state.uri.queryParameters['name'] ?? '';
              return CustomerStatementScreen(customerId: id, customerName: name);
            },
          ),

          // الموردين (Suppliers)
          GoRoute(
            path: '/suppliers',
            name: 'suppliers',
            builder: (context, state) => const SuppliersListScreen(),
          ),
          GoRoute(
            path: '/suppliers/create',
            name: 'create_supplier',
            builder: (context, state) => const SupplierFormScreen(),
          ),
          GoRoute(
            path: '/suppliers/:id',
            name: 'edit_supplier',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return SupplierFormScreen(supplierId: id);
            },
          ),
          GoRoute(
            path: '/suppliers/:id/statement',
            name: 'supplier_statement',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              final name = state.uri.queryParameters['name'] ?? '';
              return SupplierStatementScreen(supplierId: id, supplierName: name);
            },
          ),

          // المنتجات (Products)
          GoRoute(
            path: '/products',
            name: 'products',
            builder: (context, state) => const ProductsListScreen(),
          ),
          GoRoute(
            path: '/products/create',
            name: 'create_product',
            builder: (context, state) => const ProductFormScreen(),
          ),
          GoRoute(
            path: '/products/:id',
            name: 'edit_product',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return ProductFormScreen(productId: id);
            },
          ),

          // الفواتير (Invoicing)
          GoRoute(
            path: '/invoices',
            name: 'invoices',
            builder: (context, state) => const InvoiceListScreen(),
          ),
          GoRoute(
            path: '/invoices/create',
            name: 'create_invoice',
            builder: (context, state) => const InvoiceCreateScreen(),
          ),
          GoRoute(
            path: '/invoices/:id',
            name: 'invoice_detail',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return InvoiceDetailScreen(invoiceId: id);
            },
          ),

          // الصناديق (Funds)
          GoRoute(
            path: '/funds',
            name: 'funds',
            builder: (context, state) => const FundListScreen(),
          ),
          GoRoute(
            path: '/funds/create',
            name: 'create_fund',
            builder: (context, state) => const FundFormScreen(),
          ),
          GoRoute(
            path: '/funds/transfer',
            name: 'fund_transfer',
            builder: (context, state) => const FundTransferScreen(),
          ),
          GoRoute(
            path: '/funds/:id/detail',
            name: 'fund_detail',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              final name = state.uri.queryParameters['name'] ?? '';
              return FundDetailScreen(fundId: id, fundName: name);
            },
          ),
          GoRoute(
            path: '/funds/:id',
            name: 'edit_fund',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return FundFormScreen(fundId: id);
            },
          ),

          // المشتريات (Purchasing)
          GoRoute(
            path: '/purchase-orders',
            name: 'purchase_orders',
            builder: (context, state) => const PurchaseOrderListScreen(),
          ),
          GoRoute(
            path: '/purchase-orders/create',
            name: 'create_purchase_order',
            builder: (context, state) => const PurchaseOrderFormScreen(),
          ),
          GoRoute(
            path: '/purchase-orders/:id',
            name: 'purchase_order_detail',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return PurchaseOrderFormScreen(orderId: id, readOnly: true);
            },
          ),

          // الدفعات (Payments)
          GoRoute(
            path: '/payments',
            name: 'payments',
            builder: (context, state) => const PaymentListScreen(),
          ),
          GoRoute(
            path: '/payments/create',
            name: 'create_payment',
            builder: (context, state) => const PaymentFormScreen(),
          ),
          GoRoute(
            path: '/payments/:id',
            name: 'payment_detail',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return PaymentFormScreen(paymentId: id, readOnly: true);
            },
          ),

          // المستخدمين (Users)
          GoRoute(
            path: '/users',
            name: 'users',
            builder: (context, state) => const UsersListScreen(),
          ),
          GoRoute(
            path: '/users/create',
            name: 'create_user',
            builder: (context, state) => const UserFormScreen(),
          ),
          GoRoute(
            path: '/users/:id',
            name: 'edit_user',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return UserFormScreen(userId: id);
            },
          ),
          GoRoute(
            path: '/roles',
            name: 'roles',
            builder: (context, state) => const RolesScreen(),
          ),

          // التقارير (Reports)
          GoRoute(
            path: '/reports/trial-balance',
            name: 'trial_balance_report',
            builder: (context, state) => const TrialBalanceReportScreen(),
          ),
          GoRoute(
            path: '/reports/income-statement',
            name: 'income_statement',
            builder: (context, state) => const IncomeStatementScreen(),
          ),
          GoRoute(
            path: '/reports/balance-sheet',
            name: 'balance_sheet',
            builder: (context, state) => const BalanceSheetScreen(),
          ),

          // سير العمل والاعتمادات (Workflows & Approvals)
          GoRoute(
            path: '/workflows',
            name: 'workflows',
            builder: (context, state) => const WorkflowsScreen(),
          ),
          GoRoute(
            path: '/approvals',
            name: 'approvals',
            builder: (context, state) => const ApprovalsScreen(),
          ),

          // الإشعارات (Notifications)
          GoRoute(
            path: '/notifications',
            name: 'notifications',
            builder: (context, state) => const NotificationsScreen(),
          ),

          // سجل التدقيق (Audit)
          GoRoute(
            path: '/audit',
            name: 'audit',
            builder: (context, state) => const AuditScreen(),
          ),

          // العملات والمواقع (Currencies, Sites, Centers)
          GoRoute(
            path: '/currencies',
            name: 'currencies',
            builder: (context, state) => const CurrenciesScreen(),
          ),
          GoRoute(
            path: '/sites',
            name: 'sites',
            builder: (context, state) => const SitesScreen(),
          ),
          GoRoute(
            path: '/centers',
            name: 'centers',
            builder: (context, state) => const CentersScreen(),
          ),
          GoRoute(
            path: '/branches',
            name: 'branches',
            builder: (context, state) => const BranchesScreen(),
          ),

          // الأصول الثابتة والمخزون (Assets & Inventory)
          GoRoute(
            path: '/assets',
            name: 'assets',
            builder: (context, state) => const AssetsScreen(),
          ),
          GoRoute(
            path: '/inventory',
            name: 'inventory',
            builder: (context, state) => const InventoryScreen(),
          ),

          // المحاسبة الإضافية (Additional Accounting)
          GoRoute(
            path: '/fiscal-periods',
            name: 'fiscal_periods',
            builder: (context, state) => const FiscalPeriodsScreen(),
          ),
          GoRoute(
            path: '/accounts/create',
            name: 'create_account',
            builder: (context, state) {
              final parent = state.uri.queryParameters['parent'];
              return AccountFormScreen(parentCode: parent);
            },
          ),
          GoRoute(
            path: '/accounts/:code/edit',
            name: 'edit_account',
            builder: (context, state) {
              final code = state.pathParameters['code']!;
              return AccountFormScreen(accountCode: code);
            },
          ),
          GoRoute(
            path: '/general-ledger',
            name: 'general_ledger',
            builder: (context, state) => const GeneralLedgerScreen(),
          ),
          GoRoute(
            path: '/opening-balances',
            name: 'opening_balances',
            builder: (context, state) => const OpeningBalancesScreen(),
          ),

          // التقارير الإضافية (Additional Reports)
          GoRoute(
            path: '/reports/cash-flow',
            name: 'cash_flow',
            builder: (context, state) => const CashFlowScreen(),
          ),
          GoRoute(
            path: '/reports/aging',
            name: 'aging_report',
            builder: (context, state) => const AgingReportScreen(),
          ),
          GoRoute(
            path: '/reports/reconciliation',
            name: 'reconciliation',
            builder: (context, state) => const ReconciliationScreen(),
          ),
          GoRoute(
            path: '/reports/budgets',
            name: 'budgets',
            builder: (context, state) => const BudgetsScreen(),
          ),

          // الملف الشخصي (Profile)
          GoRoute(
            path: '/profile',
            name: 'profile',
            builder: (context, state) => const ProfileScreen(),
          ),

          // الإعدادات (Settings)
          GoRoute(
            path: '/settings',
            name: 'settings',
            builder: (context, state) => const SettingsScreen(),
          ),

          // صفحة 404 (غير موجودة)
          GoRoute(
            path: '/:path',
            name: 'not_found',
            builder: (context, state) => Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.error_outline, size: 80, color: Colors.grey.shade400),
                  const SizedBox(height: 16),
                  Text(
                    'الصفحة غير موجودة',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: () => context.go('/'),
                    icon: const Icon(Icons.dashboard),
                    label: const Text('العودة للوحة التحكم'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    ],
  );
}