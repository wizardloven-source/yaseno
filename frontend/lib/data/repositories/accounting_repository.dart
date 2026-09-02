import 'package:decimal/decimal.dart';
import '../../domain/entities/journal_entry.dart';
import '../../domain/entities/account.dart';
import '../../services/api_client.dart';

class AccountingRepository {
  final ApiClient _apiClient;

  AccountingRepository(this._apiClient);

  Future<List<JournalEntry>> getJournalEntries({
    DateTime? fromDate,
    DateTime? toDate,
    String? status,
    String? userId,
  }) async {
    final query = <String, dynamic>{};
    if (fromDate != null) query['from_date'] = fromDate.toIso8601String();
    if (toDate != null) query['to_date'] = toDate.toIso8601String();
    if (status != null) query['status'] = status;
    if (userId != null) query['user_id'] = userId;

    final response = await _apiClient.dio.get('/journal-entries', queryParameters: query);
    final data = response.data;
    final items = data['data'] ?? [];
    if (items is List) {
      return items.map((json) => JournalEntry.fromJson(json as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<JournalEntry> getJournalEntry(String id) async {
    final response = await _apiClient.dio.get('/journal-entries/$id');
    return JournalEntry.fromJson(response.data['data']);
  }

  Future<JournalEntry> createJournalEntry({
    required DateTime date,
    required String description,
    required List<JournalLine> lines,
    String? transactionType,
    String? createdBy,
  }) async {
    final body = {
      'date': date.toIso8601String(),
      'description': description,
      'lines': lines.map((l) => l.toJson()).toList(),
      'transactionType': transactionType,
      'createdBy': createdBy,
    };

    final response = await _apiClient.dio.post('/journal-entries', data: body);
    return JournalEntry.fromJson(response.data['data']);
  }

  Future<JournalEntry> updateJournalEntry({
    required String id,
    required DateTime date,
    required String description,
    required List<JournalLine> lines,
    required int version,
    String? transactionType,
  }) async {
    final body = {
      'date': date.toIso8601String(),
      'description': description,
      'lines': lines.map((l) => l.toJson()).toList(),
      'transactionType': transactionType,
      'version': version,
    };

    final response = await _apiClient.dio.put('/journal-entries/$id', data: body);
    return JournalEntry.fromJson(response.data['data']);
  }

  Future<JournalEntry> postJournalEntry(String id, String postedBy) async {
    final body = {'postedBy': postedBy};
    final response = await _apiClient.dio.post('/journal-entries/$id/post', data: body);
    return JournalEntry.fromJson(response.data['data']);
  }

  Future<JournalEntry> reverseJournalEntry({
    required String id,
    required String reason,
    required String reversedBy,
  }) async {
    final body = {
      'reason': reason,
      'reversedBy': reversedBy,
    };
    final response = await _apiClient.dio.post('/journal-entries/$id/reverse', data: body);
    return JournalEntry.fromJson(response.data['data']);
  }

  Future<void> deleteDraftJournalEntry(String id) async {
    await _apiClient.dio.delete('/journal-entries/$id');
  }

  Future<List<Account>> getAccounts() async {
    final response = await _apiClient.dio.get('/accounts');
    final data = response.data;
    final accountsList = data['data']?['accounts'] ?? data['data'] ?? [];
    if (accountsList is List) {
      return accountsList.map((json) => Account.fromJson(json as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<Account> createAccount({
    required String code,
    required String name,
    required String accountType,
    String? parentCode,
    String? description,
    String currency = 'USD',
  }) async {
    final body = {
      'code': code,
      'name': name,
      'accountType': accountType,
      'parentCode': parentCode,
      'description': description,
      'currency': currency,
    };
    final response = await _apiClient.dio.post('/accounts', data: body);
    return Account.fromJson(response.data['data']);
  }

  Future<Account> updateAccount({
    required String code,
    required String name,
    required String accountType,
    required bool isActive,
    String? parentCode,
    String? description,
    String currency = 'USD',
  }) async {
    final body = {
      'name': name,
      'accountType': accountType,
      'isActive': isActive,
      'parentCode': parentCode,
      'description': description,
      'currency': currency,
    };
    final response = await _apiClient.dio.put('/accounts/$code', data: body);
    return Account.fromJson(response.data['data']);
  }
}
