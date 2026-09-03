import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../providers/accounting_provider.dart';
import '../../../domain/entities/journal_entry.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/status_chip.dart';

class JournalEntryListScreen extends StatefulWidget {
  const JournalEntryListScreen({super.key});

  @override
  State<JournalEntryListScreen> createState() => _JournalEntryListScreenState();
}

class _JournalEntryListScreenState extends State<JournalEntryListScreen> {
  final _searchController = TextEditingController();
  String _statusFilter = 'all';
  String _searchText = '';
  DateTime? _fromDate;
  DateTime? _toDate;

  @override
  void initState() {
    super.initState();
    _loadEntries();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadEntries() async {
    await context.read<AccountingProvider>().loadJournalEntries(
      isPosted: _statusFilter == 'all' ? null : _statusFilter == 'posted',
      fromDate: _fromDate,
      toDate: _toDate,
    );
  }

  Future<void> _selectDate(BuildContext context, bool isFrom) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    
    if (picked != null) {
      setState(() {
        if (isFrom) {
          _fromDate = picked;
        } else {
          _toDate = picked;
        }
      });
      _loadEntries();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          context.push('/journal-entries/create').then((_) => _loadEntries());
        },
        icon: const Icon(Icons.add),
        label: const Text('قيد جديد'),
      ),
      body: Column(
        children: [
          Consumer<AccountingProvider>(
            builder: (context, provider, _) {
              if (provider.error != null) {
                return MaterialBanner(
                  content: Text('${provider.error}'),
                  leading: const Icon(Icons.wifi_off, color: AppColors.warning),
                  actions: [
                    TextButton(onPressed: _loadEntries, child: const Text('إعادة المحاولة')),
                  ],
                  backgroundColor: AppColors.warningContainer,
                );
              }
              return const SizedBox.shrink();
            },
          ),
          Container(
            padding: const EdgeInsets.all(AppDimens.s3),
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              boxShadow: AppDimens.cardShadow,
            ),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: 'ابحث في القيود...',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppDimens.radiusInput),
                    ),
                    filled: true,
                    fillColor: AppColors.surfaceContainerHigh,
                  ),
                  onChanged: (value) {
                    setState(() => _searchText = value);
                  },
                ),
                const SizedBox(height: 12),
                
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          border: Border.all(color: AppColors.outline),
                          borderRadius: BorderRadius.circular(AppDimens.radiusInput),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _statusFilter,
                            isExpanded: true,
                            items: const [
                              DropdownMenuItem(value: 'all', child: Text('الكل')),
                              DropdownMenuItem(value: 'posted', child: Text('مرحّل')),
                              DropdownMenuItem(value: 'draft', child: Text('مسودة')),
                            ],
                            onChanged: (value) {
                              setState(() => _statusFilter = value!);
                              _loadEntries();
                            },
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _selectDate(context, true),
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _fromDate != null
                              ? DateFormat('MM/dd').format(_fromDate!)
                              : 'من',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _selectDate(context, false),
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _toDate != null
                              ? DateFormat('MM/dd').format(_toDate!)
                              : 'إلى',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          
          Expanded(
            child: Consumer<AccountingProvider>(
              builder: (context, provider, child) {
                if (provider.isLoading) {
                  return const LoadingState();
                }
                
                if (provider.journalEntries.isEmpty) {
                  return EmptyState(
                    icon: Icons.book_outlined,
                    title: 'لا توجد قيود',
                    message: 'ابدأ بإنشاء قيد يومي جديد',
                    actionLabel: 'إنشاء قيد جديد',
                    onAction: () {
                      context.push('/journal-entries/create');
                    },
                  );
                }

                var entries = provider.journalEntries;
                if (_searchText.isNotEmpty) {
                  final q = _searchText.toLowerCase();
                  entries = entries.where((e) =>
                    (e.number ?? '').toLowerCase().contains(q) ||
                    e.description.toLowerCase().contains(q)
                  ).toList();
                }

                return RefreshIndicator(
                  onRefresh: _loadEntries,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(AppDimens.s3),
                    itemCount: entries.length,
                    itemBuilder: (context, index) {
                      final entry = entries[index];
                      return _buildEntryCard(entry);
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEntryCard(JournalEntry entry) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimens.radiusCard)),
      child: InkWell(
        onTap: () {
          context.push('/journal-entries/${entry.id}').then((_) => _loadEntries());
        },
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        child: Padding(
          padding: const EdgeInsets.all(AppDimens.s3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(AppDimens.s2),
                    decoration: BoxDecoration(
                      color: entry.isPosted ? AppColors.successContainer : AppColors.warningContainer,
                      borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                    ),
                    child: Icon(
                      entry.isPosted ? Icons.check_circle : Icons.edit,
                      color: entry.isPosted ? AppColors.success : AppColors.warning,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          entry.description,
                          style: AppTextStyles.titleMedium,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          DateFormat('yyyy-MM-dd').format(entry.date),
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  StatusChip(status: entry.isPosted ? 'posted' : 'draft'),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 8),
              
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildAmountItem('مدين', entry.totalDebit, AppColors.success),
                  _buildAmountItem('دائن', entry.totalCredit, AppColors.danger),
                  _buildAmountItem('الأسطر', entry.lines.length.toDouble(), AppColors.secondary),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAmountItem(String label, dynamic value, Color color) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            color: AppColors.textSecondary,
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value is Decimal
              ? formatMoney(value)
              : NumberFormat.currency(locale: 'ar', symbol: '').format(value),
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.bold,
            fontSize: 14,
          ),
        ),
      ],
    );
  }
}
