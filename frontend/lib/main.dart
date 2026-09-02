import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:ya_seen_erp_flutter/routes/app_router.dart';
import 'package:ya_seen_erp_flutter/services/api_client.dart';
import 'package:ya_seen_erp_flutter/presentation/providers/auth_provider.dart';
import 'package:ya_seen_erp_flutter/presentation/providers/accounting_provider.dart';
import 'package:ya_seen_erp_flutter/presentation/providers/funds_provider.dart';
import 'package:ya_seen_erp_flutter/presentation/providers/invoicing_provider.dart';
import 'package:ya_seen_erp_flutter/presentation/providers/purchasing_provider.dart';
import 'package:ya_seen_erp_flutter/presentation/providers/theme_provider.dart';
import 'package:ya_seen_erp_flutter/theme/app_theme.dart';

void _handleError(Object error, StackTrace stack) {
  debugPrint('=== UNCAUGHT ERROR ===');
  debugPrint('$error');
  debugPrint('$stack');
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  ErrorWidget.builder = (details) => Material(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 48),
          const SizedBox(height: 12),
          Text(details.exception.toString(), textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12)),
        ],
      ),
    ),
  );
  runZonedGuarded(() async {
    await ApiClient().init();
    final authProvider = AuthProvider();
    final themeProvider = ThemeProvider();
    await themeProvider.load();
    if (ApiClient().isAuthenticated) {
      await authProvider.loadCurrentUser();
    }
    runApp(MyApp(authProvider: authProvider, themeProvider: themeProvider));
  }, _handleError);
}

class MyApp extends StatelessWidget {
  const MyApp({super.key, required this.authProvider, required this.themeProvider});

  final AuthProvider authProvider;
  final ThemeProvider themeProvider;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: authProvider),
        ChangeNotifierProvider.value(value: themeProvider),
        ChangeNotifierProvider(create: (_) => AccountingProvider()),
        ChangeNotifierProvider(create: (_) => FundsProvider()),
        ChangeNotifierProvider(create: (_) => InvoicingProvider()),
        ChangeNotifierProvider(create: (_) => PurchasingProvider()),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) => MaterialApp.router(
          title: 'YAseen ERP',
          locale: const Locale('ar'),
          supportedLocales: const [Locale('ar'), Locale('en')],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          theme: AppTheme.light,
          darkTheme: AppTheme.dark,
          themeMode: themeProvider.mode,
          routerConfig: AppRouter.router,
          debugShowCheckedModeBanner: false,
        ),
      ),
    );
  }
}
