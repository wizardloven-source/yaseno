import 'package:flutter/material.dart';
import '../../theme/app_text_styles.dart';

class StatsCardWidget extends StatelessWidget {
  final String title;
  final String value;
  final double change;
  final IconData icon;
  final Color color;

  const StatsCardWidget({
    super.key,
    required this.title,
    required this.value,
    required this.change,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final onSurface = Theme.of(context).colorScheme.onSurface;
    final onSurfaceVar = Theme.of(context).colorScheme.onSurfaceVariant;
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: TextStyle(fontSize: 14, color: onSurfaceVar),
                ),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, color: color, size: 20),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: isDark ? DarkText.text : null,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(
                  change >= 0 ? Icons.arrow_upward : Icons.arrow_downward,
                  color: change >= 0
                      ? (isDark ? DarkText.success : Colors.green)
                      : (isDark ? DarkText.danger : Colors.red),
                  size: 16,
                ),
                const SizedBox(width: 4),
                Text(
                  '${change >= 0 ? '+' : ''}${change.toStringAsFixed(1)}%',
                  style: TextStyle(
                    color: change >= 0
                        ? (isDark ? DarkText.success : Colors.green)
                        : (isDark ? DarkText.danger : Colors.red),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  'منذ الشهر الماضي',
                  style: TextStyle(fontSize: 12, color: onSurfaceVar),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
