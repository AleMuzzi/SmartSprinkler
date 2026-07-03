import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smartsprinkler_app/data/water_alert_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('WaterAlertService notification logic', () {
    late StreamController<Map<String, dynamic>?> serviceEvents;
    late bool notificationShown;
    late String lastApiUrl;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      serviceEvents = StreamController<Map<String, dynamic>?>.broadcast();
      notificationShown = false;
      lastApiUrl = '';
    });

    tearDown(() {
      serviceEvents.close();
    });

    test('saves alert=true to SharedPreferences', () async {
      await WaterAlertService.clearAlertState();
      await WaterAlertService.setLastAlertState(true);
      final state = await WaterAlertService.getLastAlertState();
      expect(state, isTrue);
    });

    test('saves alert=false to SharedPreferences', () async {
      await WaterAlertService.clearAlertState();
      await WaterAlertService.setLastAlertState(false);
      final state = await WaterAlertService.getLastAlertState();
      expect(state, isFalse);
    });

    test('getLastAlertState returns false when no saved state', () async {
      SharedPreferences.setMockInitialValues({});
      final state = await WaterAlertService.getLastAlertState();
      expect(state, isFalse);
    });

    test('clearAlertState removes saved state', () async {
      await WaterAlertService.setLastAlertState(true);
      await WaterAlertService.clearAlertState();
      final state = await WaterAlertService.getLastAlertState();
      expect(state, isFalse);
    });
  });

  group('WaterAlertService integration', () {
    test('getLastAlertState + setLastAlertState roundtrip', () async {
      SharedPreferences.setMockInitialValues({});
      await WaterAlertService.clearAlertState();

      await WaterAlertService.setLastAlertState(true);
      expect(await WaterAlertService.getLastAlertState(), isTrue);

      await WaterAlertService.setLastAlertState(false);
      expect(await WaterAlertService.getLastAlertState(), isFalse);

      await WaterAlertService.clearAlertState();
      expect(await WaterAlertService.getLastAlertState(), isFalse);
    });
  });

  group('WaterAlertService foreground tracking', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
    });

    test('isAppForeground returns false by default', () async {
      expect(await WaterAlertService.isAppForeground(), isFalse);
    });

    test('setAppForeground(true) updates state', () async {
      await WaterAlertService.setAppForeground(true);
      expect(await WaterAlertService.isAppForeground(), isTrue);
    });

    test('setAppForeground(false) updates state', () async {
      await WaterAlertService.setAppForeground(true);
      await WaterAlertService.setAppForeground(false);
      expect(await WaterAlertService.isAppForeground(), isFalse);
    });

    test('foreground state persists across calls', () async {
      await WaterAlertService.setAppForeground(true);
      expect(await WaterAlertService.isAppForeground(), isTrue);
      expect(await WaterAlertService.isAppForeground(), isTrue);
    });
  });
}
