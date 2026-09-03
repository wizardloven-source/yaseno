import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'sidebar_widget.dart';
import '../../theme/app_dimensions.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  static const _mobileBreakpoint = 800.0;

  /// يحدد علامة التبويب النشطة في شريط التنقل السفلي حسب المسار (§54).
  static int _activeTabFor(String route) {
    if (route == '/' || route.startsWith('/dashboard')) return 0;
    if (route.startsWith('/invoices') ||
        route.startsWith('/customers') ||
        route.startsWith('/payments')) {
      return 1;
    }
    if (route.startsWith('/inventory') ||
        route.startsWith('/products') ||
        route.startsWith('/assets')) {
      return 2;
    }
    return 3;
  }

  @override
  Widget build(BuildContext context) {
    final currentRoute = GoRouterState.of(context).matchedLocation;
    final isSmallScreen = MediaQuery.of(context).size.width < _mobileBreakpoint;

    if (isSmallScreen) {
      return Scaffold(
        appBar: _buildNavbar(context, leading: Builder(
          builder: (ctx) => IconButton(
            icon: const Icon(Icons.menu),
            onPressed: () => Scaffold.of(ctx).openDrawer(),
          ),
        )),
        drawer: Drawer(
          child: SidebarWidget(currentRoute: currentRoute),
        ),
        body: child,
        floatingActionButton: _buildFloatingActions(context),
        bottomNavigationBar: _buildBottomNavigation(context, currentRoute),
      );
    }

    return Scaffold(
      body: Row(
        children: [
          SidebarWidget(currentRoute: currentRoute),
          const VerticalDivider(width: 1),
          Expanded(
            child: Column(
              children: [
                _buildNavbar(context),
                Expanded(child: child),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// زر `+` المركزي على الجوال لفتح الإجراءات السريعة (§54).
  Widget _buildFloatingActions(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return FloatingActionButton(
      onPressed: () => _showQuickActions(context),
      backgroundColor: scheme.primary,
      foregroundColor: scheme.onPrimary,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: const Icon(Icons.add, size: 28),
    );
  }

  void _showQuickActions(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: Text(
                  'إجراءات سريعة',
                  style: Theme.of(ctx).textTheme.titleMedium,
                ),
              ),
              _quickAction(ctx, Icons.receipt_long, 'فاتورة مبيعات', '/invoices/create'),
              _quickAction(ctx, Icons.shopping_cart, 'أمر شراء', '/purchase-orders/create'),
              _quickAction(ctx, Icons.payments, 'دفعة', '/payments/create'),
              _quickAction(ctx, Icons.swap_horiz, 'تحويل بين الصناديق', '/funds/transfer'),
              _quickAction(ctx, Icons.menu_book, 'قيد يومي', '/journal-entries/create'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _quickAction(BuildContext context, IconData icon, String label, String route) {
    return ListTile(
      leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(label),
      onTap: () {
        Navigator.pop(context);
        context.go(route);
      },
    );
  }

  Widget _buildBottomNavigation(BuildContext context, String currentRoute) {
    final scheme = Theme.of(context).colorScheme;
    final active = _activeTabFor(currentRoute);

    return NavigationBar(
      height: 68,
      backgroundColor: Theme.of(context).colorScheme.surface,
      indicatorColor: scheme.primary.withValues(alpha: 0.15),
      selectedIndex: active,
      onDestinationSelected: (index) {
        switch (index) {
          case 0:
            context.go('/');
          case 1:
            context.go('/invoices');
          case 2:
            context.go('/inventory');
          case 3:
            Scaffold.of(context).openDrawer();
        }
      },
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'الرئيسية',
        ),
        NavigationDestination(
          icon: Icon(Icons.sell_outlined),
          selectedIcon: Icon(Icons.sell),
          label: 'المبيعات',
        ),
        NavigationDestination(
          icon: Icon(Icons.inventory_2_outlined),
          selectedIcon: Icon(Icons.inventory_2),
          label: 'المخزون',
        ),
        NavigationDestination(
          icon: Icon(Icons.more_horiz),
          selectedIcon: Icon(Icons.more_horiz),
          label: 'المزيد',
        ),
      ],
    );
  }

  /// الشريط العلوي: ارتفاع 64، قابل للتكيّف مع الثيم.
  PreferredSizeWidget _buildNavbar(BuildContext context, {Widget? leading}) {
    final scheme = Theme.of(context).colorScheme;
    return AppBar(
      toolbarHeight: AppDimens.navbarHeight,
      leading: leading,
      titleSpacing: 16,
      title: SizedBox(
        height: AppDimens.inputHeight,
        child: TextField(
          decoration: InputDecoration(
            hintText: 'بحث...',
            prefixIcon: const Icon(Icons.search, size: 20),
            isDense: true,
            filled: true,
            fillColor: scheme.surface,
            contentPadding: const EdgeInsets.symmetric(horizontal: 16),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: BorderSide(color: scheme.outlineVariant),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: BorderSide(color: scheme.primary),
            ),
          ),
        ),
      ),
      actions: [
        IconButton(
          icon: const Icon(Icons.notifications_outlined),
          onPressed: () => context.go('/notifications'),
          tooltip: 'الإشعارات',
        ),
        CircleAvatar(
          radius: 16,
          backgroundColor: scheme.primary,
          child: IconButton(
            icon: Icon(Icons.person, size: 20, color: scheme.onPrimary),
            onPressed: () => context.go('/profile'),
            padding: EdgeInsets.zero,
            tooltip: 'الملف الشخصي',
          ),
        ),
        const SizedBox(width: 16),
      ],
    );
  }
}
