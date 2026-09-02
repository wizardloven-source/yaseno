// lib/presentation/widgets/excel_import_screen.dart
// شاشة استيراد إكسل احترافية: اختيار ملف → مطابقة أعمدة → استيراد مع شريط تقدم → ملخص النتائج.
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/import/excel_import_engine.dart';
import '../../services/import/import_definitions.dart';

/// يفتح الشاشة من أي مكان.
Future<void> showExcelImport({
  required BuildContext context,
  required ImportEntityType type,
}) async {
  await Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => ExcelImportScreen(type: type),
    ),
  );
}

class ExcelImportScreen extends StatefulWidget {
  final ImportEntityType type;

  const ExcelImportScreen({super.key, required this.type});

  @override
  State<ExcelImportScreen> createState() => _ExcelImportScreenState();
}

class _ExcelImportScreenState extends State<ExcelImportScreen> {
  final ExcelImportEngine _engine = ExcelImportEngine();
  late final List<ImportField> _fields = _fieldsFor(widget.type);

  final ApiService _api = ApiService();
  String _baseCurrency = 'USD';

  int _step = 0; // 0 = اختيار، 1 = مطابقة، 2 = تقدم، 3 = نتيجة

  // حالة الملف
  String? _fileName;
  ExcelAnalysis? _analysis;

  // حالة المطابقة
  final Map<String, int> _mapping = {};

  // حالة الاستيراد
  bool _importing = false;
  int _done = 0;
  int _total = 0;
  ImportSummary? _summary;
  String? _fatalError;

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
  }

  Future<void> _loadBaseCurrency() async {
    try {
      final res = await _api.get('currency/base');
      final code = res['code'] ?? res['data'];
      if (mounted && code != null) {
        setState(() => _baseCurrency = code.toString());
      }
    } catch (_) {}
  }

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
        withData: true,
      );
      if (result == null || result.files.isEmpty) return;
      final file = result.files.single;
      final bytes = file.bytes;
      if (bytes == null) {
        _showError('تعذّر قراءة الملف. تأكد من أنه ملف .xlsx صالح.');
        return;
      }
      await _analyze(bytes, file.name);
    } catch (e) {
      _showError('تعذّر فتح الملف: ${e.toString().length > 120 ? 'صيغة غير مدعومة' : e}');
    }
  }

  Future<void> _analyze(Uint8List bytes, String name) async {
    setState(() {
      _fatalError = null;
      _fileName = name;
    });
    try {
      final analysis = await _engine.analyzeFile(bytes, _fields);
      final auto = _engine.autoMapColumns(analysis.headers, _fields);
      if (!mounted) return;
      setState(() {
        _analysis = analysis;
        _mapping
          ..clear()
          ..addAll(auto);
        _step = 1;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _fatalError = e.toString();
          _fileName = null;
        });
      }
    }
  }

  Future<void> _startImport() async {
    final analysis = _analysis;
    if (analysis == null) return;
    setState(() {
      _step = 2;
      _done = 0;
      _total = analysis.rows.length;
      _summary = null;
      _importing = true;
    });

    final summary = await _engine.importRows(
      type: widget.type,
      fields: _fields,
      rows: analysis.rows,
      columnMapping: _mapping,
      baseCurrency: _baseCurrency,
      onProgress: (done, total) {
        if (mounted) setState(() => _done = done);
      },
    );

    if (mounted) {
      setState(() {
        _summary = summary;
        _done = summary.total;
        _importing = false;
      });
      await Future<void>.delayed(const Duration(milliseconds: 600));
      if (mounted) setState(() => _step = 3);
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  List<Map<String, String>> get _previewRows {
    final a = _analysis;
    if (a == null) return const [];
    final n = a.rows.length > 6 ? 6 : a.rows.length;
    return a.rows.sublist(0, n);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.type.title),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _buildStepper(),
              const SizedBox(height: 16),
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 250),
                  child: _buildStep(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStepper() {
    const labels = [
      'اختيار الملف',
      'مطابقة الأعمدة',
      'الاستيراد',
      'النتيجة',
    ];
    return Row(
      children: [
        for (var i = 0; i < 4; i++) ...[
          Expanded(
            child: Column(
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _step > i
                        ? Colors.green
                        : _step == i
                            ? Theme.of(context).colorScheme.primary
                            : Theme.of(context).colorScheme.surfaceContainerHighest,
                  ),
                  alignment: Alignment.center,
                  child: _step > i
                      ? const Icon(Icons.check, color: Colors.white, size: 18)
                      : Text(
                          '${i + 1}',
                          style: TextStyle(
                            color: _step == i ? Colors.white : Theme.of(context).colorScheme.onSurfaceVariant,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
                const SizedBox(height: 6),
                Text(
                  labels[i],
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight:
                        _step == i ? FontWeight.bold : FontWeight.normal,
                    color: _step == i
                        ? Theme.of(context).colorScheme.onSurface
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          if (i < 3)
            Container(
              width: 12,
              height: 2,
              margin: const EdgeInsets.only(bottom: 22),
              color: _step > i ? Colors.green : Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
        ],
      ],
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case 0:
        return _buildFileStep();
      case 1:
        return _buildMappingStep();
      case 2:
        return _buildProgressStep();
      default:
        return _buildResultStep();
    }
  }

  // ------------------------------------------------------------------ الخطوة 0
  Widget _buildFileStep() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(8),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.file_present, size: 96, color: Colors.green.shade300),
            const SizedBox(height: 16),
            Text('استيراد من ملف إكسل (.xlsx)',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              '${_fields.length} حقل مدعوم · حتى 1000 صف',
              style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 24),
            if (_fatalError != null) ...[
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: Colors.red),
                      const SizedBox(width: 8),
                      Expanded(
                          child: Text(_fatalError!,
                              style: const TextStyle(fontSize: 12))),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
            if (_fileName != null) ...[
              Chip(
                avatar: const Icon(Icons.description, size: 18),
                label: Text(_fileName!),
              ),
              const SizedBox(height: 12),
            ],
            ElevatedButton.icon(
              onPressed: _pickFile,
              icon: const Icon(Icons.upload_file),
              label: const Text('اختيار ملف إكسل'),
              style: ElevatedButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
                textStyle: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'النظام يكتشف رؤوس الأعمدة تلقائياً، ويمكنك تعديل المطابقة قبل الاستيراد.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  // ------------------------------------------------------------------ الخطوة 1
  Widget _buildMappingStep() {
    final analysis = _analysis;
    if (analysis == null) {
      return const Center(child: Text('لا توجد بيانات'));
    }
    final required = _fields.where((f) => f.required).toList();
    final mappedRequired =
        required.where((f) => _mapping.containsKey(f.key)).length;

    return Column(
      children: [
        Card(
          color: Colors.amber.shade50,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                const Icon(Icons.info_outline, color: Colors.amber),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'تم اكتشاف ${analysis.headers.length} عموداً و ${analysis.rows.length} صفاً. تأكد من تطابق الحقول المطلوبة ثم ابدأ الاستيراد.',
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView(
            children: [
              _buildMappingPanel(),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(8),
                        child: Text(
                          'معاينة البيانات (أول ${_previewRows.length} صف)',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                      ),
                      const Divider(height: 1),
                      _buildPreviewTable(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () {
                  setState(() {
                    _analysis = null;
                    _fileName = null;
                    _step = 0;
                  });
                },
                icon: const Icon(Icons.arrow_back),
                label: const Text('اختيار ملف آخر'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ElevatedButton.icon(
                onPressed: mappedRequired == required.length
                    ? _startImport
                    : null,
                icon: const Icon(Icons.play_arrow),
                label: Text(
                    _importing ? 'جارٍ الاستيراد...' : 'بدء الاستيراد (${analysis.rows.length} صف)'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMappingPanel() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('مطابقة الأعمدة',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 8),
            ..._fields.map((field) => _buildMappingRow(field)),
          ],
        ),
      ),
    );
  }

  Widget _buildMappingRow(ImportField field) {
    final analysis = _analysis!;
    final missing = !_mapping.containsKey(field.key);
    final isMapped = !missing;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Row(
              children: [
                if (field.required)
                  const Text('*',
                      style: TextStyle(color: Colors.red)),
                const SizedBox(width: 2),
                Expanded(
                  child: Text(field.label,
                      style: const TextStyle(fontSize: 13),
                      overflow: TextOverflow.ellipsis),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: DropdownButton<int>(
              isExpanded: true,
              value: _mapping[field.key],
              hint: Text(
                field.required ? 'اختر العمود...' : 'تجاهل',
                style: TextStyle(fontSize: 13, color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
              items: [
                if (!field.required)
                  const DropdownMenuItem<int>(
                    value: -1,
                    child: Text('تجاهل', style: TextStyle(fontSize: 13)),
                  ),
                for (var h = 0; h < analysis.headers.length; h++)
                  DropdownMenuItem<int>(
                    value: h,
                    child: Text(
                      'العمود ${_letter(h)} (${analysis.headers[h]})',
                      style: const TextStyle(fontSize: 13),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: (v) {
                final value = v == -1 ? null : v;
                setState(() {
                  if (value == null) {
                    _mapping.remove(field.key);
                  } else {
                    _mapping[field.key] = value;
                  }
                });
              },
            ),
          ),
          const SizedBox(width: 8),
          Icon(isMapped ? Icons.check_circle : Icons.error_outline,
              color: isMapped ? Colors.green : Colors.orange, size: 20),
        ],
      ),
    );
  }

  Widget _buildPreviewTable() {
    final analysis = _analysis!;
    final rows = _previewRows;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowHeight: 36,
        dataRowMinHeight: 32,
        dataRowMaxHeight: 32,
        columnSpacing: 14,
        columns: [
          const DataColumn(label: Text('#', style: TextStyle(fontSize: 12))),
          for (var h = 0; h < analysis.headers.length; h++)
            DataColumn(
              label: Text(
                '${_letter(h)}${analysis.headers[h].length > 10 ? '\n${analysis.headers[h]}' : ''}',
                style: const TextStyle(fontSize: 11),
              ),
            ),
        ],
        rows: [
          for (var r = 0; r < rows.length; r++)
            DataRow(cells: [
              DataCell(Text('${r + 1}', style: const TextStyle(fontSize: 11))),
              for (var h = 0; h < analysis.headers.length; h++)
                DataCell(
                  Text(
                    rows[r]['col$h'] ?? '',
                    style: const TextStyle(fontSize: 11),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  // عارض اقتراح
                  placeholder: true,
                ),
            ]),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------ الخطوة 2
  Widget _buildProgressStep() {
    final progress = _total == 0 ? 0.0 : _done / _total;
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SvgLikeProgress(progress: progress),
            const SizedBox(height: 24),
            Text(
              _importing
                  ? 'جارٍ استيراد البيانات...'
                  : 'اكتمل الاستيراد',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              '$_done من $_total',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Text(
              '${(progress * 100).toStringAsFixed(0)}%',
              style: TextStyle(
                color: Theme.of(context).colorScheme.primary,
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 12,
                backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
            ),
            const SizedBox(height: 16),
            if (_importing)
              Text('يرجى عدم إغلاق الشاشة أثناء الاستيراد',
                  style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  // ------------------------------------------------------------------ الخطوة 3
  Widget _buildResultStep() {
    final summary = _summary;
    if (summary == null) return const SizedBox.shrink();
    final failed = summary.failed;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(8),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              failed == 0 ? Icons.check_circle : Icons.warning_amber,
              size: 96,
              color: failed == 0 ? Colors.green : Colors.orange,
            ),
            const SizedBox(height: 16),
            Text(
              failed == 0 ? 'تم الاستيراد بنجاح!' : 'اكتمل الاستيراد مع أخطاء',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                _resultChip('الإجمالي', '${summary.total}', Colors.blueGrey),
                _resultChip('الناجح', '${summary.success}', Colors.green),
                _resultChip('المرفوض', '${summary.failed}', Colors.red),
                _resultChip('الوقت', '${(summary.durationMs / 1000).toStringAsFixed(1)} ث', Colors.purple),
              ],
            ),
            const SizedBox(height: 20),
            if (failed > 0) _buildErrorList(),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton.icon(
                  onPressed: () {
                    setState(() {
                      _analysis = null;
                      _fileName = null;
                      _summary = null;
                      _step = 0;
                    });
                  },
                  icon: const Icon(Icons.replay),
                  label: const Text('استيراد ملف آخر'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: () => Navigator.of(context).pop(true),
                  icon: const Icon(Icons.done),
                  label: const Text('إغلاق'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorList() {
    final failedRows = _summary!.results
        .where((r) => !r.success)
        .toList()
      ..sort((a, b) => a.rowNumber.compareTo(b.rowNumber));
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'تفاصيل الأخطاء',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 180),
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: failedRows.length > 50 ? 50 : failedRows.length,
                itemBuilder: (_, i) {
                  final r = failedRows[i];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.red.shade100,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text('صف ${r.rowNumber}',
                              style: const TextStyle(fontSize: 11)),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(r.error ?? '',
                              style: const TextStyle(fontSize: 12)),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _resultChip(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(value,
              style: TextStyle(
                  fontSize: 22, fontWeight: FontWeight.bold, color: color)),
          Text(label, style: TextStyle(fontSize: 12, color: color)),
        ],
      ),
    );
  }

  String _letter(int index) {
    var n = index + 1;
    var s = '';
    while (n > 0) {
      final rem = (n - 1) % 26;
      s = String.fromCharCode(65 + rem) + s;
      n = (n - 1) ~/ 26;
    }
    return s;
  }
}

/// قائمة الحقول حسب النوع (تُبنى لمرة واحدة).
List<ImportField> _fieldsFor(ImportEntityType type) {
  switch (type) {
    case ImportEntityType.customers:
      return customerFields;
    case ImportEntityType.products:
      return productFields;
    case ImportEntityType.invoices:
      return invoiceFields;
  }
}

/// عنصر تقدم دائري برسوم SVG خفيفة عبر Canvas.
class SvgLikeProgress extends StatelessWidget {
  final double progress;
  const SvgLikeProgress({super.key, required this.progress});

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return SizedBox(
      width: 120,
      height: 120,
      child: CustomPaint(
        painter: _ProgressPainter(progress: progress, color: color),
      ),
    );
  }
}

class _ProgressPainter extends CustomPainter {
  final double progress;
  final Color color;
  _ProgressPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    const stroke = 12.0;
    final rect = Rect.fromCircle(
      center: Offset(size.width / 2, size.height / 2),
      radius: size.width / 2 - stroke / 2,
    );
    final track = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..color = color.withOpacity(0.15);
    canvas.drawArc(rect, 0, math.pi * 2, false, track);

    final arc = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round
      ..color = color;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2 * progress.clamp(0.0, 1.0),
        false, arc);

    final tp = TextPainter(
      text: TextSpan(
        text: '${(progress * 100).toStringAsFixed(0)}%',
        style: TextStyle(
            fontSize: 22, fontWeight: FontWeight.bold, color: color),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, Offset(size.width / 2 - tp.width / 2,
        size.height / 2 - tp.height / 2));
  }

  @override
  bool shouldRepaint(_ProgressPainter old) =>
      old.progress != progress || old.color != color;
}
