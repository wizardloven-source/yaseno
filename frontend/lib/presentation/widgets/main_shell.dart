import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'sidebar_widget.dart';
import '../../theme/app_dimensions.dart';
import '../../theme/app_colors.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final currentRoute = GoRouterState.of(context).matchedLocation;
    final isSmallScreen = MediaQuery.of(context).size.width < 800;

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
