import 'dart:async';
import 'dart:convert';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const notificationChannelId = 'water_alert_channel';
const notificationId = 999;
const prefsKeyWaterAlert = 'water_low_alert_last';
const prefsKeyAppForeground = 'app_in_foreground';

Future<void> _showNotification() async {
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

Future<void> _saveAlertState(bool alert) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool(prefsKeyWaterAlert, alert);
}

@pragma('vm:entry-point')
void onStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();

  String apiUrl = '';
  bool lastAlertState = false;

  service.on('setUrl').listen((data) {
    if (data != null && data['url'] != null) {
      apiUrl = data['url'] as String;
    }
  });

  service.on('stop').listen((event) {
    service.stopSelf();
  });

  Timer.periodic(const Duration(seconds: 3), (timer) async {
    if (apiUrl.isEmpty) return;

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
              await _showNotification();
            }
          }
        }
      }
    } catch (e) {
      debugPrint('WaterAlertService background error: $e');
    }
  });
}

class WaterAlertService {
  static final FlutterBackgroundService _service = FlutterBackgroundService();
  static final WaterAlertService _instance = WaterAlertService._();
  factory WaterAlertService() => _instance;
  WaterAlertService._();

  bool _initialized = false;

  Future<void> init(String apiUrl) async {
    if (_initialized) return;
    _initialized = true;

    final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
        FlutterLocalNotificationsPlugin();

    const androidChannel = AndroidNotificationChannel(
      notificationChannelId,
      'Water Alert',
      description: 'Notifications when water tank is low',
      importance: Importance.high,
    );

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(androidChannel);

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

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
}
