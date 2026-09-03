import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimensions.dart';

/// LoadingState — حالة التحميل الموحّدة (§58.3، §52).
///
/// يعرض هيكلاً عظميًا (skeleton) أو مؤشر تقدم بدلًا من تجميد الشاشة.
class LoadingState extends StatelessWidget {
  final bool skeleton;
  final int skeletonLines;

  const LoadingState({
    super.key,
    this.skeleton = true,
    this.skeletonLines = 6,
  });

  @override
  Widget build(BuildContext context) {
    if (!skeleton) {
      return const Center(child: CircularProgressIndicator());
    }
    return _SkeletonList(lines: skeletonLines);
  }
}

class _SkeletonList extends StatelessWidget {
  final int lines;
  const _SkeletonList({required this.lines});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final base = isDark ? const Color(0xFF1C1C1E) : const Color(0xFFEEF1F5);
    final highlight = isDark ? const Color(0xFF2A2A2E) : const Color(0xFFF7F8FA);

    return Shimmer.fromColors(
      baseColor: base,
      highlightColor: highlight,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        physics: const NeverScrollableScrollPhysics(),
        itemCount: lines,
        itemBuilder: (context, index) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Container(
            height: 76,
            padding: const EdgeInsets.all(AppDimens.s3),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF0D0D0D) : Colors.white,
              borderRadius: BorderRadius.circular(AppDimens.radiusCard),
              border: Border.all(
                color: isDark ? const Color(0xFF1C1C1E) : AppColors.cardBorder,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: base,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(width: double.infinity, height: 12, color: base),
                      const SizedBox(height: 8),
                      Container(width: 140, height: 10, color: base),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
