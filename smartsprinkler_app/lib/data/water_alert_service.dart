import 'dart:async';
import 'dart:convert';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smartsprinkler_app/data/models/watering_report.dart';
import 'package:smartsprinkler_app/ui/dashboard/watering_report_dialog.dart';

const notificationChannelId = 'water_alert_channel';
const reportNotificationChannelId = 'watering_report_channel';
const notificationId = 999;
const prefsKeyWaterAlert = 'water_low_alert_last';
const prefsKeyAppForeground = 'app_in_foreground';

/// Highest watering-report id already surfaced on this device. Persisted so
/// a service restart never replays old proposals.
const prefsKeyWateringReportLast = 'watering_report_last_id';

/// System-notification ids for watering reports live above the water-alert
/// one so the two streams never overwrite each other.
int wateringReportNotificationId(int reportId) => 1000 + reportId;

Future<void> _saveAlertState(bool alert) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool(prefsKeyWaterAlert, alert);
}

/// Highest report id in [items], or 0 when the list is empty.
int highestWateringReportId(List<Map<String, dynamic>> items) {
  var highest = 0;
  for (final item in items) {
    final id = (item['id'] as num?)?.toInt() ?? 0;
    if (id > highest) highest = id;
  }
  return highest;
}

/// Reports created after [lastReportId] that nobody has opened yet — the
/// exact set the app must surface (history is never replayed, entries the
/// portal or another client already opened are skipped).
List<Map<String, dynamic>> freshWateringReports(
  List<Map<String, dynamic>> items,
  int lastReportId,
) {
  return items.where((item) {
    final id = (item['id'] as num?)?.toInt() ?? 0;
    return id > lastReportId && item['unread'] == true;
  }).toList();
}

@pragma('vm:entry-point')
void onStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();

  String apiUrl = '';
  String bayesianUrl = '';
  bool lastAlertState = false;

  final prefs = await SharedPreferences.getInstance();
  var lastReportId = prefs.getInt(prefsKeyWateringReportLast) ?? -1;

  service.on('setUrl').listen((data) {
    if (data != null && data['url'] != null) {
      apiUrl = data['url'] as String;
    }
  });

  service.on('setBayesianUrl').listen((data) {
    if (data != null && data['url'] != null) {
      bayesianUrl = data['url'] as String;
    }
  });

  service.on('stop').listen((event) {
    service.stopSelf();
  });

  // Use a longer interval to reduce battery usage and main thread load
  Timer.periodic(const Duration(seconds: 30), (timer) async {
    if (apiUrl.isNotEmpty) {
      try {
        final response = await http.get(
          Uri.parse('$apiUrl/water_alert'),
        ).timeout(const Duration(seconds: 10));

        if (response.statusCode == 200) {
          final json = jsonDecode(response.body) as Map<String, dynamic>;
          final alert = json['alert'] == true;

          if (alert != lastAlertState) {
            lastAlertState = alert;
            await _saveAlertState(alert);
            if (alert) {
              final inForeground = await WaterAlertService.isAppForeground();
              if (!inForeground) {
                // Invoke platform channel to show notification in main isolate
                service.invoke('showNotification');
              }
            }
          }
        }
      } catch (e) {
        debugPrint('WaterAlertService background error: $e');
      }
    }

    if (bayesianUrl.isEmpty) return;

    // Watering proposals: the server computes the doses in notification mode
    // and never dispenses. Surface every report created since the last poll.
    try {
      final response = await http.get(
        Uri.parse('$bayesianUrl/api/notifications?limit=20'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) return;

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final items = (json['notifications'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .toList();

      final highest = highestWateringReportId(items);

      if (lastReportId < 0) {
        // First poll after a fresh install: adopt the current history as the
        // baseline instead of replaying proposals the user never saw here.
        lastReportId = highest;
        await prefs.setInt(prefsKeyWateringReportLast, lastReportId);
        return;
      }

      final fresh = freshWateringReports(items, lastReportId);

      if (highest > lastReportId) {
        lastReportId = highest;
        await prefs.setInt(prefsKeyWateringReportLast, lastReportId);
      }

      for (final item in fresh) {
        service.invoke('showWateringReport', {'report': item});
      }
    } catch (e) {
      debugPrint('Watering report poll error: $e');
    }
  });
}

class WaterAlertService {
  static final FlutterBackgroundService _service = FlutterBackgroundService();
  static final WaterAlertService _instance = WaterAlertService._();
  factory WaterAlertService() => _instance;
  WaterAlertService._();

  bool _initialized = false;
  static final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();

  Future<void> init(String apiUrl, {String? bayesianUrl}) async {
    if (_initialized) return;
    _initialized = true;

    const androidChannel = AndroidNotificationChannel(
      notificationChannelId,
      'Water Alert',
      description: 'Notifications when water tank is low',
      importance: Importance.high,
    );

    const reportChannel = AndroidNotificationChannel(
      reportNotificationChannelId,
      'Watering proposals',
      description: 'Notifications when plants need watering',
      importance: Importance.high,
    );

    final androidPlugin = _notifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(androidChannel);
    await androidPlugin?.createNotificationChannel(reportChannel);
    await androidPlugin?.requestNotificationsPermission();

    // Tapping a watering-proposal notification re-opens the report.
    await _notifications.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );

    // Set up handler for 'showNotification' from background isolate
    _service.on('showNotification').listen((_) {
      _showNotificationInMain();
    });

    // Watering proposals raised by the background poll.
    _service.on('showWateringReport').listen((event) {
      _handleWateringReport(event);
    });

    await _service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: onStart,
        autoStart: true,
        isForegroundMode: false,
        autoStartOnBoot: true,
        notificationChannelId: notificationChannelId,
        initialNotificationTitle: 'SmartSprinkler',
        initialNotificationContent: 'Monitoring water level',
        foregroundServiceNotificationId: notificationId,
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: onStart,
      ),
    );

    _service.invoke('setUrl', {'url': apiUrl});
    if (bayesianUrl != null && bayesianUrl.isNotEmpty) {
      _service.invoke('setBayesianUrl', {'url': bayesianUrl});
    }
  }

  /// Refreshes the server URL held by the background isolate. The effective
  /// URL can change at runtime (LAN/external switch), so this is called
  /// whenever the app comes back to the foreground.
  void updateBayesianUrl(String url) {
    if (url.isEmpty) return;
    _service.invoke('setBayesianUrl', {'url': url});
  }

  Future<void> start() async {
    await _service.startService();
  }

  Future<bool> ensureNotificationPermission() async {
    final FlutterLocalNotificationsPlugin plugin = FlutterLocalNotificationsPlugin();
    final granted = await plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
    return granted ?? true;
  }

  void stop() {
    _service.invoke('stop');
  }

  static Future<bool> getLastAlertState() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(prefsKeyWaterAlert) ?? false;
  }

  static Future<void> setLastAlertState(bool alert) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(prefsKeyWaterAlert, alert);
  }

  static Future<void> clearAlertState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(prefsKeyWaterAlert);
  }

  static Future<void> setAppForeground(bool foreground) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(prefsKeyAppForeground, foreground);
  }

  static Future<bool> isAppForeground() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(prefsKeyAppForeground) ?? false;
  }

  /// System notification for a watering proposal raised by the background
  /// poll while the app is not on screen. The payload carries the whole
  /// report so tapping it needs no extra fetch.
  static Future<void> _showWateringReportNotification(
      WateringReport report) async {
    const androidDetails = AndroidNotificationDetails(
      reportNotificationChannelId,
      'Watering proposals',
      channelDescription: 'Notifications when plants need watering',
      importance: Importance.high,
      priority: Priority.high,
      icon: 'ic_bg_service_small',
    );
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      wateringReportNotificationId(report.id),
      report.title,
      report.body,
      details,
      payload: jsonEncode(report.toJson()),
    );
  }

  /// Entry point for a proposal raised while the app is on screen: show the
  /// report directly instead of posting a system notification.
  static Future<void> _handleWateringReport(dynamic event) async {
    final raw = event is Map ? event['report'] : null;
    if (raw is! Map) return;

    try {
      final report = WateringReport.fromJson(Map<String, dynamic>.from(raw));
      final inForeground = await isAppForeground();
      if (inForeground) {
        await showWateringReportDialog(report);
      } else {
        await _showWateringReportNotification(report);
      }
    } catch (e) {
      debugPrint('Watering report handling error: $e');
    }
  }

  /// User tapped a watering-proposal system notification.
  void _onNotificationTapped(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) return;
    try {
      final json = jsonDecode(payload) as Map<String, dynamic>;
      showWateringReportDialog(WateringReport.fromJson(json));
    } catch (e) {
      debugPrint('Watering report payload error: $e');
    }
  }

  // Called from background isolate via platform channel
  static Future<void> _showNotificationInMain() async {
    final FlutterLocalNotificationsPlugin notifications = FlutterLocalNotificationsPlugin();

    const androidDetails = AndroidNotificationDetails(
      notificationChannelId,
      'Water Alert',
      channelDescription: 'Notifications when water tank is low',
      importance: Importance.high,
      priority: Priority.high,
      icon: 'ic_bg_service_small',
    );
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await notifications.show(
      notificationId,
      'Water Tank Low!',
      'The water tank is running low. Please refill.',
      details,
    );
  }
}
