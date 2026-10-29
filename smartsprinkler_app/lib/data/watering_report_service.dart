import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/data/models/watering_report.dart';
import 'package:smartsprinkler_app/data/settings.dart';

/// Client for the server-side watering notification centre.
///
/// The server owns the history and the unread badge so the mobile app and
/// the web portal always agree on what has already been seen.
class WateringReportService {
  WateringReportService({Settings? settings, http.Client? client})
      : _settings = settings ?? Settings(),
        _client = client ?? http.Client();

  final Settings _settings;
  final http.Client _client;
  static const Duration _timeout = Duration(seconds: 10);

  Future<List<WateringReport>> fetchReports({int limit = 50}) async {
    final response = await _client
        .get(Uri.parse('${_settings.bayesianUrl}/api/notifications?limit=$limit'))
        .timeout(_timeout);
    if (response.statusCode != 200) {
      throw Exception('notifications fetch failed: ${response.statusCode}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final items = json['notifications'] as List<dynamic>? ?? const [];
    return items
        .map((item) => WateringReport.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// Marks one report as opened (clears the unread badge for both clients).
  Future<void> markOpened(int id) => _post('open', id);

  /// Marks one report as read (used by the "mark as read" affordance).
  Future<void> markRead(int id) => _post('read', id);

  /// Clears the whole badge at once.
  Future<void> markAllRead() async {
    final response = await _client
        .post(Uri.parse('${_settings.bayesianUrl}/api/notifications/read-all'))
        .timeout(_timeout);
    if (response.statusCode != 200) {
      throw Exception('notifications read-all failed: ${response.statusCode}');
    }
  }

  Future<void> _post(String action, int id) async {
    final response = await _client
        .post(Uri.parse('${_settings.bayesianUrl}/api/notifications/$id/$action'))
        .timeout(_timeout);
    if (response.statusCode != 200) {
      throw Exception('notification $action failed: ${response.statusCode}');
    }
  }
}
