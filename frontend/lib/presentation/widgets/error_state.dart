import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimensions.dart';
import '../../theme/app_text_styles.dart';

/// ErrorState — حالة الخطأ الموحّدة (§113، §50).
///
/// كل خطأ يجيب عن: ماذا حدث؟ لماذا؟ ماذا أفعل؟
/// مع زر إعادة المحاولة عند توفره.
class ErrorState extends StatelessWidget {
  final String title;
  final String? message;
  final String? hint;
  final VoidCallback? onRetry;

  const ErrorState({
    super.key,
    this.title = 'حدث خطأ',
    this.message,
    this.hint,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final Color accent = isDark ? AppColors.errorLight : AppColors.error;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.error_outline, size: 40, color: accent),
            ),
            const SizedBox(height: AppDimens.s3),
            Text(
              title,
              style: AppTextStyles.headlineSmall,
              textAlign: TextAlign.center,
            ),
            if (message != null && message!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                message!,
                style: AppTextStyles.bodyMediumFor(context).copyWith(
                  color: scheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (hint != null && hint!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                hint!,
                style: AppTextStyles.bodySmallFor(context),
                textAlign: TextAlign.center,
              ),
            ],
            if (onRetry != null) ...[
              const SizedBox(height: AppDimens.s4),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 20),
                label: const Text('إعادة المحاولة'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
