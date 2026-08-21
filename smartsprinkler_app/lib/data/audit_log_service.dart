import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/data/settings.dart';

class AuditLogEntry {
  final int id;
  final String timestamp;
  final String category;
  final String message;
  final String? details;
  final String source;
  final String? level;
  final String? event;
  final String? fw;

  AuditLogEntry({
    required this.id,
    required this.timestamp,
    required this.category,
    required this.message,
    this.details,
    this.source = 'server',
    this.level,
    this.event,
    this.fw,
  });

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) {
    return AuditLogEntry(
      id: json['id'] as int,
      timestamp: json['timestamp'] as String,
      category: json['category'] as String,
      message: json['message'] as String,
      details: json['details'] as String?,
      source: json['source'] as String? ?? 'server',
      level: json['level'] as String?,
      event: json['event'] as String?,
      fw: json['fw'] as String?,
    );
  }
}

class AuditLogService {
  final Settings settings = Settings();

  /// Fetch log entries from the combined server + ESP endpoint. ``source``
  /// is one of ``all`` / ``server`` / ``esp``. ``levelMin`` is the minimum
  /// severity to include (debug < info < warn < error); default ``info``
  /// hides debug noise. Pass ``debug`` to see every entry.
  Future<List<AuditLogEntry>> fetchLogEntries({
    String source = 'all',
    String filter = '',
    String? category,
    String levelMin = 'info',
    int limit = 200,
    String? startDate,
    String? endDate,
  }) async {
    final query = <String, String>{
      'source': source,
      'level_min': levelMin,
    };
    if (filter.isNotEmpty) query['filter'] = filter;
    if (category != null && category.isNotEmpty) query['category'] = category;
    if (limit != 200) query['limit'] = limit.toString();
    if (startDate != null) query['start_date'] = startDate;
    if (endDate != null) query['end_date'] = endDate;

    final uri = Uri.parse('${settings.bayesianUrl}/api/logs').replace(
      queryParameters: query.isEmpty ? null : query,
    );

    final response = await http.get(uri).timeout(const Duration(seconds: 10));
    if (response.statusCode != 200) {
      throw Exception('Log fetch failed: ${response.statusCode}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final entries = (json['entries'] as List<dynamic>)
        .map((e) => AuditLogEntry.fromJson(e as Map<String, dynamic>))
        .toList();
    return entries;
  }

  /// Deletes log entries (server, ESP, or both via ``source``). When a date
  /// range is supplied only the entries within it (inclusive) are removed,
  /// otherwise everything.
  Future<int> deleteLogEntries({
    String source = 'all',
    String? startDate,
    String? endDate,
  }) async {
    final query = <String, String>{'source': source};
    if (startDate != null) query['start_date'] = startDate;
    if (endDate != null) query['end_date'] = endDate;

    final uri = Uri.parse('${settings.bayesianUrl}/api/logs').replace(
      queryParameters: query.isEmpty ? null : query,
    );

    final response = await http.delete(uri).timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw Exception('Log delete failed: ${response.statusCode}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return json['deleted'] as int? ?? 0;
  }

  /// Downloads the combined log as a CSV file. Returns the file path where
  /// it was saved and the suggested filename (or null if the server
  /// didn't provide one).
  Future<({String path, String? suggestedName})> downloadCsv({
    String source = 'all',
    String filter = '',
    String? category,
    String levelMin = 'info',
  }) async {
    final query = <String, String>{
      'source': source,
      'level_min': levelMin,
    };
    if (filter.isNotEmpty) query['filter'] = filter;
    if (category != null && category.isNotEmpty) query['category'] = category;

    final uri = Uri.parse('${settings.bayesianUrl}/api/logs/export').replace(
      queryParameters: query.isEmpty ? null : query,
    );

    final response = await http.get(uri).timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) {
      throw Exception('Log export failed: ${response.statusCode}');
    }

    // Parse Content-Disposition for the suggested filename.
    String? suggested;
    final cd = response.headers['content-disposition'];
    if (cd != null) {
      final m = RegExp(r'filename="?([^";]+)"?').firstMatch(cd);
      if (m != null) suggested = m.group(1);
    }
    suggested ??= 'logs_${DateTime.now().millisecondsSinceEpoch}.csv';

    // Pick a sensible Downloads directory on each platform.
    final dir = await _downloadsDir();
    final path = '$dir/$suggested';
    final file = File(path);
    await file.writeAsBytes(response.bodyBytes);
    return (path: path, suggestedName: suggested);
  }

  Future<String> _downloadsDir() async {
    // iOS / Android: use the app documents directory. Desktop / fallback
    // could be a "Downloads" folder, but we keep it platform-neutral
    // here to avoid pulling in path_provider at this layer.
    return Directory.systemTemp.path;
  }
}