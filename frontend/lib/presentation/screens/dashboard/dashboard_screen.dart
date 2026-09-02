import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  String? _error;
  String _companyName = 'Ya Seen ERP';
  String _currencySymbol = 'د.ع';

  int _journalCount = 0;
  int _invoiceCount = 0;
  int _paymentCount = 0;
  int _fundCount = 0;

  Decimal _totalRevenue = Decimal.zero;
  Decimal _totalPayments = Decimal.zero;
  Decimal _totalBalance = Decimal.zero;
  int _lowStockCount = 0;
  int _pendingPayments = 0;
  List<Map<String, dynamic>> _recentJournals = [];
  List<Map<String, dynamic>> _recentInvoices = [];

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    bool anySuccess = false;

    // Load settings
    try {
      final settings = await _api.getSettings();
      if (mounted) {
        setState(() => _companyName = settings['company_name'] ?? 'Ya Seen ERP');
      }
      anySuccess = true;
    } catch (_) {}

    // Load currency
    try {
      final baseRes = await _api.get('currency/base');
      final baseData = baseRes['data'];
      final symbol = (baseData is Map ? baseData['symbol'] : null) ?? 'د.ع';
      if (mounted) setState(() => _currencySymbol = symbol);
    } catch (_) {}

    // Load counts (each independently)
    try {
      final journalData = await _api.get('journal-entries');
      final journalItems = journalData['items'] ?? [];
      if (mounted) setState(() => _journalCount = journalItems is List ? journalItems.length : 0);
      anySuccess = true;
    } catch (_) {}

    try {
      final invoiceData = await _api.get('invoices');
      final invoiceItems = invoiceData['items'] ?? [];
      if (mounted) setState(() => _invoiceCount = invoiceItems is List ? invoiceItems.length : 0);
      anySuccess = true;
    } catch (_) {}

    try {
      final paymentData = await _api.get('payments');
      final paymentItems = paymentData['items'] ?? [];
      if (mounted) setState(() => _paymentCount = paymentItems is List ? paymentItems.length : 0);
      anySuccess = true;
    } catch (_) {}

    try {
      final fundData = await _api.get('funds');
      final fundItems = fundData['items'] ?? [];
      if (mounted) setState(() => _fundCount = fundItems is List ? fundItems.length : 0);
      anySuccess = true;
    } catch (_) {}

    // Load financial summary
    try {
      final trialBalance = await _api.getTrialBalanceReport(DateTime.now());
      final trialData = trialBalance['data'] ?? trialBalance;
      final entries = trialData['entries'] ?? trialData['items'] ?? [];
      if (entries is List) {
        Decimal totalDebit = Decimal.zero;
        Decimal totalCredit = Decimal.zero;
        for (final entry in entries) {
          totalDebit += parseMoney(entry['debit']) ?? Decimal.zero;
          totalCredit += parseMoney(entry['credit']) ?? Decimal.zero;
        }
        if (mounted) setState(() => _totalBalance = totalDebit - totalCredit);
      }
    } catch (_) {}

    // Load recent journals
    try {
      final journalsResp = await _api.get('journal-entries', queryParameters: {'limit': 5});
      final journalItems = journalsResp['items'] ?? journalsResp['data'] ?? [];
      if (mounted && journalItems is List) {
        setState(() => _recentJournals = journalItems.cast<Map<String, dynamic>>());
      }
    } catch (_) {}

    // Load recent invoices and compute revenue
    try {
      final invoicesResp = await _api.get('invoices', queryParameters: {'limit': 5});
      final invoiceItems = invoicesResp['items'] ?? invoicesResp['data'] ?? [];
      if (mounted && invoiceItems is List) {
        final items = invoiceItems.cast<Map<String, dynamic>>();
        Decimal revenue = Decimal.zero;
        for (final inv in items) {
          revenue += parseMoney(inv['total'] ?? inv['amount']) ?? Decimal.zero;
        }
        setState(() {
          _recentInvoices = items;
          _totalRevenue = revenue;
        });
      }
    } catch (_) {}

    // Load payments total
    try {
      final paymentsResp = await _api.get('payments', queryParameters: {'limit': 100});
      final payItems = paymentsResp['items'] ?? paymentsResp['data'] ?? [];
      if (payItems is List) {
        Decimal totalPaid = Decimal.zero;
        int pending = 0;
        for (final p in payItems) {
          totalPaid += parseMoney(p['amount']) ?? Decimal.zero;
          if (p['status'] == 'pending') pending++;
        }
        if (mounted) {
          setState(() {
            _totalPayments = totalPaid;
            _pendingPayments = pending;
          });
        }
      }
    } catch (_) {}

    // Load low stock
    try {
      final lowStock = await _api.get('inventory/low-stock');
      final lowItems = lowStock['items'] ?? lowStock['data'] ?? [];
      if (mounted && lowItems is List) {
        setState(() => _lowStockCount = lowItems.length);
      }
    } catch (_) {}

    if (mounted) {
      setState(() {
        _isLoading = false;
        if (!anySuccess) {
          _error = 'لا يمكن الاتصال بالخادم. تأكد من تشغيل الخادم على المنفذ 8000.';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_companyName),
        centerTitle: true,
        automaticallyImplyLeading: false,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, color: AppColors.dashboardRed, size: 64),
                      const SizedBox(height: 16),
                      Text(
                        'حدث خطأ',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        ErrorUtils.sanitize(_error),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: _loadDashboard,
                        icon: const Icon(Icons.refresh),
                        label: const Text('إعادة المحاولة'),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadDashboard,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _buildWelcomeHeader(),
                      const SizedBox(height: 20),
                      _buildSummaryCards(),
                      const SizedBox(height: 24),
                      _buildQuickActions(),
                      const SizedBox(height: 24),
                      _buildFinancialSummary(),
                      const SizedBox(height: 24),
                      _buildRecentActivity(),
                      const SizedBox(height: 24),
                      _buildAlerts(),
                    ],
                  ),
                ),
    );
  }

  Widget _buildWelcomeHeader() {
    final now = DateTime.now();
    final hour = now.hour;
    String greeting;
    if (hour < 12) {
      greeting = 'صباح الخير';
    } else if (hour < 17) {
      greeting = 'مساء النهار';
    } else {
      greeting = 'مساء الخير';
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppColors.headerGradient,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$greeting!',
            style: const TextStyle(
              color: AppColors.textOnPrimary,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'مرحباً بك في $_companyName',
            style: TextStyle(
              color: AppColors.textOnPrimary.withOpacity(0.9),
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCards() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'ملخص النظام',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.5,
          children: [
            _buildSummaryCard(
              title: 'القيود اليومية',
              count: _journalCount,
              icon: Icons.book,
              color: AppColors.dashboardBlue,
              route: '/journal-entries',
            ),
            _buildSummaryCard(
              title: 'الفواتير',
              count: _invoiceCount,
              icon: Icons.receipt_long,
              color: AppColors.dashboardGreen,
              route: '/invoices',
            ),
            _buildSummaryCard(
              title: 'المدفوعات',
              count: _paymentCount,
              icon: Icons.payments,
              color: AppColors.dashboardOrange,
              route: '/payments',
            ),
            _buildSummaryCard(
              title: 'الصناديق',
              count: _fundCount,
              icon: Icons.account_balance_wallet,
              color: AppColors.dashboardPurple,
              route: '/funds',
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSummaryCard({
    required String title,
    required int count,
    required IconData icon,
    required Color color,
    required String route,
  }) {
    return GestureDetector(
      onTap: () => context.go(route),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Theme.of(context).brightness == Brightness.dark ? Colors.black26 : AppColors.cardShadow,
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$count',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'إجراءات سريعة',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        _buildActionTile(
          icon: Icons.add_circle_outline,
          title: 'قيد يومي جديد',
          subtitle: 'إنشاء قيد محاسبي جديد',
          color: AppColors.dashboardBlue,
          route: '/journal-entries/create',
        ),
        _buildActionTile(
          icon: Icons.receipt_long,
          title: 'فاتورة جديدة',
          subtitle: 'إنشاء فاتورة مبيعات جديدة',
          color: AppColors.dashboardGreen,
          route: '/invoices/create',
        ),
        _buildActionTile(
          icon: Icons.payments,
          title: 'دفعة جديدة',
          subtitle: 'تسجيل دفعة جديدة',
          color: AppColors.dashboardOrange,
          route: '/payments/create',
        ),
        _buildActionTile(
          icon: Icons.swap_horiz,
          title: 'تحويل بين الصناديق',
          subtitle: 'تحويل أموال بين الصناديق',
          color: AppColors.dashboardPurple,
          route: '/funds/transfer',
        ),
      ],
    );
  }

  Widget _buildActionTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required String route,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.1),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle, style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant)),
        trailing: Icon(Icons.arrow_forward_ios, size: 16, color: Theme.of(context).colorScheme.onSurfaceVariant),
        onTap: () => context.go(route),
      ),
    );
  }

  Widget _buildFinancialSummary() {
    final outstandingBalance = _totalRevenue - _totalPayments;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'ملخص مالي',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _buildFinanceCard(
              title: 'إجمالي الإيرادات',
              value: _formatCurrency(_totalRevenue),
              color: AppColors.dashboardGreen,
              icon: Icons.trending_up,
            )),
            const SizedBox(width: 12),
            Expanded(child: _buildFinanceCard(
              title: 'إجمالي المدفوعات',
              value: _formatCurrency(_totalPayments),
              color: AppColors.dashboardOrange,
              icon: Icons.trending_down,
            )),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _buildFinanceCard(
              title: 'الرصيد المستحق',
              value: _formatCurrency(outstandingBalance),
              color: outstandingBalance >= Decimal.zero ? AppColors.dashboardBlue : AppColors.dashboardRed,
              icon: Icons.account_balance,
            )),
            const SizedBox(width: 12),
            Expanded(child: _buildFinanceCard(
              title: 'تنبيه المخزون المنخفض',
              value: '$_lowStockCount منتج',
              color: _lowStockCount > 0 ? AppColors.dashboardRed : AppColors.dashboardGreen,
              icon: Icons.warning_amber,
            )),
          ],
        ),
      ],
    );
  }

  Widget _buildFinanceCard({
    required String title,
    required String value,
    required Color color,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Theme.of(context).brightness == Brightness.dark ? Colors.black26 : AppColors.cardShadow,
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color),
          ),
        ],
      ),
    );
  }

  Widget _buildRecentActivity() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'أحدث النشاطات',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        if (_recentInvoices.isEmpty && _recentJournals.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text('لا توجد نشاطات حديثة', style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
            ),
          )
        else ...[
          if (_recentInvoices.isNotEmpty) ...[
            Text('آخر الفواتير', style: AppTextStyles.titleSmall),
            const SizedBox(height: 8),
            ..._recentInvoices.take(5).map((inv) => _buildActivityTile(
              icon: Icons.receipt_long,
              color: AppColors.dashboardGreen,
              title: inv['code'] ?? inv['invoice_number'] ?? 'فاتورة',
              subtitle: inv['customer_name'] ?? inv['counterparty'] ?? '',
              amount: parseMoney(inv['total'] ?? inv['amount']) ?? Decimal.zero,
              date: inv['date'] ?? inv['created_at'] ?? '',
            )),
          ],
          if (_recentJournals.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('آخر القيود اليومية', style: AppTextStyles.titleSmall),
            const SizedBox(height: 8),
            ..._recentJournals.take(5).map((journal) => _buildActivityTile(
              icon: Icons.book,
              color: AppColors.dashboardBlue,
              title: journal['code'] ?? journal['reference'] ?? 'قيد',
              subtitle: journal['description'] ?? journal['notes'] ?? '',
              amount: parseMoney(journal['total_debit'] ?? journal['amount']) ?? Decimal.zero,
              date: journal['date'] ?? journal['created_at'] ?? '',
            )),
          ],
        ],
      ],
    );
  }

  Widget _buildActivityTile({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required dynamic amount,
    required dynamic date,
  }) {
    String dateStr = '';
    if (date != null && date.toString().isNotEmpty) {
      dateStr = date.toString().length >= 10 ? date.toString().substring(0, 10) : date.toString();
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(10),
      ),
      child: ListTile(
        dense: true,
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.1),
          radius: 18,
          child: Icon(icon, color: color, size: 18),
        ),
        title: Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        subtitle: Text(
          '${subtitle.isNotEmpty ? subtitle : "—"} · $dateStr',
          style: TextStyle(fontSize: 11, color: Theme.of(context).colorScheme.onSurfaceVariant),
          overflow: TextOverflow.ellipsis,
        ),
        trailing: Text(
          _formatCurrency(amount),
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: color),
        ),
      ),
    );
  }

  Widget _buildAlerts() {
    final hasAlerts = _lowStockCount > 0 || _pendingPayments > 0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'تنبيهات',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        if (!hasAlerts)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Theme.of(context).brightness == Brightness.dark ? const Color(0xFF052E16) : AppColors.successContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(Icons.check_circle, color: AppColors.success),
                const SizedBox(width: 12),
                Text('لا توجد تنبيهات حالياً', style: TextStyle(color: AppColors.success, fontWeight: FontWeight.w500)),
              ],
            ),
          )
        else ...[
          if (_lowStockCount > 0)
            _buildAlertTile(
              icon: Icons.warning_amber,
              color: AppColors.dashboardRed,
              title: 'مخزون منخفض',
              subtitle: '$_lowStockCount منتج بمخزون منخفض',
              route: '/inventory',
            ),
          if (_pendingPayments > 0)
            _buildAlertTile(
              icon: Icons.pending_actions,
              color: AppColors.dashboardOrange,
              title: 'مدفوعات بانتظار الاعتماد',
              subtitle: '$_pendingPayments دفعة بانتظار الاعتماد',
              route: '/payments',
            ),
        ],
      ],
    );
  }

  Widget _buildAlertTile({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required String route,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: color.withOpacity(0.05),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.15),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(title, style: TextStyle(fontWeight: FontWeight.w600, color: color)),
        subtitle: Text(subtitle, style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant)),
        trailing: Icon(Icons.arrow_forward_ios, size: 16, color: color),
        onTap: () => context.go(route),
      ),
    );
  }

  String _formatCurrency(dynamic amount) {
    final d = parseMoney(amount);
    if (d == null) return '$_currencySymbol 0';
    if (d == d.truncate() && d.abs() < Decimal.fromInt(1000000)) {
      return '${formatMoney(d, decimals: 0)} $_currencySymbol';
    }
    return '${formatMoney(d, decimals: 2)} $_currencySymbol';
  }
}
