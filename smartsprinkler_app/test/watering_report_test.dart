import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smartsprinkler_app/data/models/watering_report.dart';
import 'package:smartsprinkler_app/data/settings.dart';
import 'package:smartsprinkler_app/data/water_alert_service.dart';
import 'package:smartsprinkler_app/data/watering_report_service.dart';

const _serverPayload = {
  'id': 12,
  'created_at': '2026-10-02T14:05:00+02:00',
  'source': 'scheduled',
  'title': '2 piante da innaffiare',
  'body': 'Habanero 138 ml, Rosmarino 69 ml — totale 207 ml',
  'doses': {'habanero': 138, 'rosmarino': 69},
  'unread': true,
  'opened_at': null,
  'read_at': null,
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('WateringReport', () {
    test('parses the server payload', () {
      final report = WateringReport.fromJson(_serverPayload);

      expect(report.id, 12);
      expect(report.source, 'scheduled');
      expect(report.title, '2 piante da innaffiare');
      expect(report.doses, {'habanero': 138.0, 'rosmarino': 69.0});
      expect(report.createdAt.year, 2026);
      expect(report.totalMl, 207.0);
    });

    test('roundtrips through the notification payload', () {
      final report = WateringReport.fromJson(_serverPayload);
      final restored = WateringReport.fromJson(
        jsonDecode(jsonEncode(report.toJson())) as Map<String, dynamic>,
      );

      expect(restored.id, report.id);
      expect(restored.title, report.title);
      expect(restored.doses, report.doses);
      expect(restored.totalMl, report.totalMl);
    });

    test('tolerates a payload without doses', () {
      final report = WateringReport.fromJson(const {
        'id': 1,
        'created_at': 'not-a-date',
        'title': 'Pianta da innaffiare',
      });

      expect(report.doses, isEmpty);
      expect(report.totalMl, 0.0);
      expect(report.source, 'scheduled');
      expect(report.createdAt, isNotNull);
    });

    test('labels known plants and falls back to the raw id', () {
      final report = WateringReport.fromJson(_serverPayload);

      expect(report.labelFor('habanero'), 'Habanero');
      expect(report.labelFor('mystery'), 'mystery');
    });
  });

  group('WateringReportService', () {
    test('fetchReports parses the notification list', () async {
      final client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/notifications');
        expect(request.url.queryParameters['limit'], '5');
        return http.Response(
          jsonEncode({
            'notifications': [_serverPayload],
            'unread_count': 1,
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final service =
          WateringReportService(settings: Settings(), client: client);
      final reports = await service.fetchReports(limit: 5);

      expect(reports, hasLength(1));
      expect(reports.first.id, 12);
      expect(reports.first.doses['habanero'], 138.0);
    });

    test('fetchReports surfaces server errors', () async {
      final client = MockClient((_) async => http.Response('boom', 500));
      final service =
          WateringReportService(settings: Settings(), client: client);

      expect(service.fetchReports, throwsA(isA<Exception>()));
    });

    test('markOpened posts to the open endpoint', () async {
      String? method;
      String? path;
      final client = MockClient((request) async {
        method = request.method;
        path = request.url.path;
        return http.Response('{"unread_count": 0}', 200);
      });

      await WateringReportService(settings: Settings(), client: client)
          .markOpened(7);

      expect(method, 'POST');
      expect(path, '/api/notifications/7/open');
    });

    test('markAllRead posts to read-all', () async {
      String? path;
      final client = MockClient((request) async {
        path = request.url.path;
        return http.Response('{"status": "ok"}', 200);
      });

      await WateringReportService(settings: Settings(), client: client)
          .markAllRead();

      expect(path, '/api/notifications/read-all');
    });
  });

  group('background poll dedup', () {
    Map<String, dynamic> item(int id, {bool unread = true}) => {
          'id': id,
          'unread': unread,
          'title': 'report $id',
          'body': '',
          'doses': <String, dynamic>{},
        };

    test('highestWateringReportId ignores empty lists', () {
      expect(highestWateringReportId(const []), 0);
      expect(
        highestWateringReportId([item(3), item(7), item(5)]),
        7,
      );
    });

    test('surfaces only reports newer than the stored mark', () {
      final fresh = freshWateringReports([item(4), item(5), item(6)], 4);
      expect(fresh.map((e) => e['id']), [5, 6]);
    });

    test('never replays history on a fresh install', () {
      expect(freshWateringReports([item(4), item(5)], 5), isEmpty);
      expect(freshWateringReports([item(4), item(5)], 6), isEmpty);
    });

    test('skips reports another client already opened', () {
      final fresh = freshWateringReports(
        [item(5, unread: false), item(6)],
        4,
      );
      expect(fresh.map((e) => e['id']), [6]);
    });
  });

  group('system notification ids', () {
    test('watering reports never collide with the water-alert one', () {
      expect(wateringReportNotificationId(1), 1001);
      expect(wateringReportNotificationId(999), 1999);
      expect(wateringReportNotificationId(1), isNot(notificationId));
    });
  });
}
