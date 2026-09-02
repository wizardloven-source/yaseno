import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/product_model.dart';
import '../../../data/repositories/product_repository.dart';
import '../../../services/import/import_definitions.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/excel_import_screen.dart';

class ProductsListScreen extends StatefulWidget {
  const ProductsListScreen({super.key});

  @override
  State<ProductsListScreen> createState() => _ProductsListScreenState();
}

class _ProductsListScreenState extends State<ProductsListScreen> {
  List<Product> _allProducts = [];
  bool _isLoading = true;
  String? _error;
  bool _includeInactive = false;
  String _searchText = '';
  String? _selectedCategory;
  bool _isGridView = true;

  List<Product> get _filteredProducts {
    var list = _allProducts;
    if (_searchText.isNotEmpty) {
      final q = _searchText.toLowerCase();
      list = list.where((p) =>
        p.name.toLowerCase().contains(q) ||
        p.code.toLowerCase().contains(q) ||
        (p.description ?? '').toLowerCase().contains(q)
      ).toList();
    }
    if (_selectedCategory != null) {
      list = list.where((p) => p.category == _selectedCategory).toList();
    }
    return list;
  }

  List<String> get _categories {
    final cats = <String>{};
    for (final p in _allProducts) {
      if (p.category != null && p.category!.isNotEmpty) cats.add(p.category!);
    }
    return cats.toList()..sort();
  }

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  Future<void> _loadProducts() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final products = await ProductRepository.getProducts(
        includeInactive: _includeInactive,
        limit: 500,
      );
      setState(() { _allProducts = products; _isLoading = false; });
    } catch (e) {
      setState(() { _error = ErrorUtils.sanitize(e); _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredProducts;
    return Scaffold(
      appBar: AppBar(
        title: const Text('المنتجات'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.file_upload_outlined),
            tooltip: 'استيراد من إكسل',
            onPressed: () => showExcelImport(
              context: context,
              type: ImportEntityType.products,
            ).then((_) => _loadProducts()),
          ),
          IconButton(
            icon: Icon(_isGridView ? Icons.view_list : Icons.grid_view),
            onPressed: () => setState(() => _isGridView = !_isGridView),
            tooltip: _isGridView ? 'عرض قائمة' : 'عرض شبكة',
          ),
          IconButton(
            icon: Icon(_includeInactive ? Icons.visibility : Icons.visibility_off),
            onPressed: () { setState(() { _includeInactive = !_includeInactive; _loadProducts(); }); },
            tooltip: 'عرض غير النشطة',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              onChanged: (v) => setState(() => _searchText = v),
              decoration: InputDecoration(
                hintText: 'بحث بالاسم أو الكود...',
                prefixIcon: const Icon(Icons.search, size: 20),
                suffixIcon: _searchText.isNotEmpty
                  ? IconButton(icon: const Icon(Icons.clear, size: 18), onPressed: () => setState(() => _searchText = ''))
                  : null,
                filled: true,
                fillColor: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.3),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppDimens.radiusInput), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                isDense: true,
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadProducts, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : Column(
                  children: [
                    if (_categories.isNotEmpty) _buildCategoryChips(),
                    _buildSummaryHeader(filtered),
                    Expanded(child: _filteredProducts.isEmpty ? _buildEmpty() : _isGridView ? _buildGrid(filtered) : _buildList(filtered)),
                  ],
                ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addProduct,
        icon: const Icon(Icons.add),
        label: const Text('منتج جديد'),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: AppColors.danger),
          const SizedBox(height: 16),
          Text(ErrorUtils.sanitize(_error)),
          const SizedBox(height: 16),
          AppButton(
            onPressed: _loadProducts,
            icon: Icons.refresh,
            label: 'إعادة المحاولة',
            variant: AppButtonVariant.primary,
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.inventory_2, size: 80, color: Theme.of(context).colorScheme.onSurfaceVariant),
          const SizedBox(height: 16),
          Text(_searchText.isNotEmpty ? 'لا توجد نتائج بحث' : 'لا يوجد منتجات', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          if (_searchText.isNotEmpty)
            TextButton(onPressed: () => setState(() { _searchText = ''; _selectedCategory = null; }), child: const Text('مسح البحث')),
        ],
      ),
    );
  }

  Widget _buildCategoryChips() {
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: FilterChip(
              label: const Text('الكل'),
              selected: _selectedCategory == null,
              onSelected: (_) => setState(() => _selectedCategory = null),
              selectedColor: AppColors.secondaryContainer,
            ),
          ),
          ..._categories.map((cat) => Padding(
            padding: const EdgeInsets.only(right: 6),
            child: FilterChip(
              label: Text(cat),
              selected: _selectedCategory == cat,
              onSelected: (_) => setState(() => _selectedCategory = _selectedCategory == cat ? null : cat),
              selectedColor: AppColors.secondaryContainer,
            ),
          )),
        ],
      ),
    );
  }

  Widget _buildSummaryHeader(List<Product> products) {
    final totalStock = products.fold<int>(0, (s, p) => s + p.stockQuantity);
    final totalValue = products.fold(Decimal.zero, (s, p) => s + (p.unitPrice * Decimal.fromInt(p.stockQuantity)));
    final lowStock = products.where((p) => p.stockQuantity > 0 && p.stockQuantity <= 10).length;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          _summaryChip('${products.length}', 'منتج', AppColors.secondary),
          const SizedBox(width: 8),
          _summaryChip('$totalStock', 'وحدة', AppColors.success),
          const SizedBox(width: 8),
          _summaryChip(formatMoney(totalValue), 'قيمة', AppColors.primary),
          if (lowStock > 0) ...[
            const SizedBox(width: 8),
            _summaryChip('$lowStock', 'مخزون منخفض', AppColors.warning),
          ],
        ],
      ),
    );
  }

  Widget _summaryChip(String value, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 13)),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(fontSize: 11, color: color.withAlpha(180))),
        ],
      ),
    );
  }

  Widget _buildGrid(List<Product> products) {
    return GridView.builder(
      padding: const EdgeInsets.all(12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3, childAspectRatio: 1.0, crossAxisSpacing: 12, mainAxisSpacing: 12,
      ),
      itemCount: products.length,
      itemBuilder: (context, i) => _buildProductCard(products[i]),
    );
  }

  Widget _buildList(List<Product> products) {
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: products.length,
      separatorBuilder: (_, __) => const SizedBox(height: 6),
      itemBuilder: (context, i) => _buildProductTile(products[i]),
    );
  }

  Widget _buildProductCard(Product product) {
    final isLow = product.stockQuantity > 0 && product.stockQuantity <= 10;
    final isOut = product.stockQuantity == 0;
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: () => _editProduct(product),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: product.isActive ? AppColors.secondaryContainer : Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(Icons.inventory_2, color: product.isActive ? AppColors.secondary : Colors.grey, size: 24),
                  ),
                  PopupMenuButton<String>(
                    itemBuilder: (_) => [
                      const PopupMenuItem(value: 'edit', child: Text('تعديل')),
                      const PopupMenuItem(value: 'stock', child: Text('تعديل المخزون')),
                      PopupMenuItem(value: 'toggle', child: Text(product.isActive ? 'إيقاف' : 'تفعيل')),
                      const PopupMenuItem(value: 'delete', child: Text('حذف', style: TextStyle(color: AppColors.danger))),
                    ],
                    onSelected: (v) => _handleAction(v, product),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(product.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14), maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 4),
              Text('الكود: ${product.code}', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              const Spacer(),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('${formatMoney(product.unitPrice)} ${product.currency}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.success, fontSize: 14)),
                  if (product.category != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(color: AppColors.primaryContainer, borderRadius: BorderRadius.circular(8)),
                      child: Text(product.category!, style: TextStyle(fontSize: 10, color: AppColors.primary)),
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isOut ? AppColors.errorContainer : isLow ? AppColors.warningContainer : AppColors.successContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(isOut ? Icons.cancel : isLow ? Icons.warning : Icons.check_circle, size: 16,
                      color: isOut ? AppColors.danger : isLow ? AppColors.warning : AppColors.success),
                    const SizedBox(width: 4),
                    Text('${product.stockQuantity} وحدة', style: TextStyle(fontWeight: FontWeight.bold,
                      color: isOut ? AppColors.danger : isLow ? AppColors.warning : AppColors.success, fontSize: 12)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProductTile(Product product) {
    final isLow = product.stockQuantity > 0 && product.stockQuantity <= 10;
    final isOut = product.stockQuantity == 0;
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: product.isActive ? AppColors.secondaryContainer : Colors.grey.shade200,
          child: Icon(Icons.inventory_2, color: product.isActive ? AppColors.secondary : Colors.grey, size: 20),
        ),
        title: Text(product.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${product.code} | ${product.category ?? "بدون تصنيف"} | ${formatMoney(product.unitPrice)} ${product.currency}'),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: isOut ? AppColors.errorContainer : isLow ? AppColors.warningContainer : AppColors.successContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text('${product.stockQuantity}', style: TextStyle(fontWeight: FontWeight.bold,
                color: isOut ? AppColors.danger : isLow ? AppColors.warning : AppColors.success)),
            ),
            PopupMenuButton<String>(
              itemBuilder: (_) => [
                const PopupMenuItem(value: 'edit', child: Text('تعديل')),
                const PopupMenuItem(value: 'stock', child: Text('تعديل المخزون')),
                PopupMenuItem(value: 'toggle', child: Text(product.isActive ? 'إيقاف' : 'تفعيل')),
                const PopupMenuItem(value: 'delete', child: Text('حذف', style: TextStyle(color: AppColors.danger))),
              ],
              onSelected: (v) => _handleAction(v, product),
            ),
          ],
        ),
        onTap: () => _editProduct(product),
      ),
    );
  }

  void _handleAction(String value, Product product) {
    switch (value) {
      case 'edit': _editProduct(product); break;
      case 'stock': _adjustStock(product); break;
      case 'toggle': _toggleProductStatus(product); break;
      case 'delete': _deleteProduct(product); break;
    }
  }

  void _addProduct() {
    context.push('/products/create').then((r) { if (r == true) _loadProducts(); });
  }

  void _editProduct(Product product) {
    context.push('/products/${product.id}').then((r) { if (r == true) _loadProducts(); });
  }

  Future<void> _toggleProductStatus(Product product) async {
    final updated = Product(
      id: product.id, code: product.code, name: product.name, unitPrice: product.unitPrice,
      currency: product.currency, description: product.description, category: product.category,
      taxRate: product.taxRate, stockQuantity: product.stockQuantity, isActive: !product.isActive,
      createdAt: product.createdAt, updatedAt: DateTime.now(), version: product.version,
    );
    final result = await ProductRepository.updateProduct(updated);
    if (result != null) {
      _loadProducts();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(updated.isActive ? 'تم تفعيل المنتج' : 'تم إيقاف المنتج'), backgroundColor: AppColors.success));
    }
  }

  Future<void> _deleteProduct(Product product) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف المنتج'),
        content: Text('هل أنت متأكد من حذف "${product.name}"؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), style: ElevatedButton.styleFrom(backgroundColor: AppColors.danger), child: const Text('حذف')),
        ],
      ),
    );
    if (confirm == true) {
      final ok = await ProductRepository.deleteProduct(product.id);
      if (ok) {
        _loadProducts();
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم حذف المنتج'), backgroundColor: AppColors.success));
      }
    }
  }

  Future<void> _adjustStock(Product product) async {
    final qtyCtrl = TextEditingController();
    final reasonCtrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تعديل المخزون'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('المنتج: ${product.name}'),
            Text('المخزون الحالي: ${product.stockQuantity}', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            TextField(controller: qtyCtrl, keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'الكمية (+ للإضافة، - للخصم)', border: OutlineInputBorder(), prefixIcon: Icon(Icons.numbers))),
            const SizedBox(height: 12),
            TextField(controller: reasonCtrl,
              decoration: const InputDecoration(labelText: 'السبب', border: OutlineInputBorder(), prefixIcon: Icon(Icons.note))),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () {
              final q = int.tryParse(qtyCtrl.text);
              if (q != null && q != 0) Navigator.pop(ctx, true);
              else ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('أدخل كمية صحيحة')));
            },
            child: const Text('تطبيق', style: TextStyle(color: AppColors.warning)),
          ),
        ],
      ),
    );
    final qty = int.tryParse(qtyCtrl.text) ?? 0;
    final reason = reasonCtrl.text;
    qtyCtrl.dispose();
    reasonCtrl.dispose();
    if (result == true) {
      final res = await ProductRepository.updateStock(product.id, qty, reason.isEmpty ? 'تعديل يدوي' : reason);
      if (res != null) {
        _loadProducts();
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('تم تحديث المخزون: ${qty > 0 ? "+" : ""}$qty'), backgroundColor: AppColors.success));
      }
    }
  }
}
