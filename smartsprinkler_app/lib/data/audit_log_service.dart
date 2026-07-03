import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/data/settings.dart';

class AuditLogEntry {
  final int id;
  final String timestamp;
  final String category;
  final String message;
  final String? details;

  AuditLogEntry({
    required this.id,
    required this.timestamp,
    required this.category,
    required this.message,
    this.details,
  });

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) {
    return AuditLogEntry(
      id: json['id'] as int,
      timestamp: json['timestamp'] as String,
      category: json['category'] as String,
      message: json['message'] as String,
      details: json['details'] as String?,
    );
  }
}

class AuditLogService {
  final Settings settings = Settings();

  Future<List<AuditLogEntry>> fetchLogEntries({
    String filter = '',
    String? category,
    int limit = 200,
  }) async {
    final query = <String, String>{};
    if (filter.isNotEmpty) query['filter'] = filter;
    if (category != null && category.isNotEmpty) query['category'] = category;
    if (limit != 200) query['limit'] = limit.toString();

    final uri = Uri.parse('${settings.bayesianUrl}/api/audit-log').replace(
      queryParameters: query.isEmpty ? null : query,
    );

    final response = await http.get(uri).timeout(const Duration(seconds: 10));
    if (response.statusCode != 200) {
      throw Exception('Audit log fetch failed: ${response.statusCode}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final entries = (json['entries'] as List<dynamic>)
        .map((e) => AuditLogEntry.fromJson(e as Map<String, dynamic>))
        .toList();
    return entries;
  }
}