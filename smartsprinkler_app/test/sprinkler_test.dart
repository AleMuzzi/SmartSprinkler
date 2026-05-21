import 'package:flutter_test/flutter_test.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';

void main() {
  group('Sprinkler singleton', () {
    test('returns same instance', () {
      final s1 = Sprinkler();
      final s2 = Sprinkler();
      expect(identical(s1, s2), isTrue);
    });

    test('starts with default values', () {
      final s = Sprinkler();
      expect(s.airHumidity, equals(0.0));
      expect(s.airTemperature, equals(0.0));
      expect(s.soilMoisture, equals(0.0));
      expect(s.waterPump, equals('off'));
      expect(s.waterLowAlert, equals(false));
      expect(s.blockedAmountMl, equals(0));
    });
  });

  group('Sprinkler.updateWithJson', () {
    test('parses full status response', () {
      final s = Sprinkler();
      s.updateWithJson({
        'air_humidity': '65.5',
        'air_temperature': '28.3',
        'soil_moisture': '42.0',
        'water_pump': 'on',
        'valve_1': 'off',
        'valve_2': 'on',
        'valve_3': 'off',
        'soil_moisture_0': '12000',
        'soil_moisture_1': '15000',
        'soil_moisture_2': '8000',
        'soil_moisture_3': '20000',
        'water_low_alert': 'off',
        'blocked_amount_ml': '0',
        'active_plant': 'NAGA_MORICH',
      });
      expect(s.airHumidity, equals(65.5));
      expect(s.airTemperature, equals(28.3));
      expect(s.soilMoisture, equals(42.0));
      expect(s.waterPump, equals('on'));
      expect(s.waterLowAlert, equals(false));
      expect(s.blockedAmountMl, equals(0));
    });

    test('parses water low alert on', () {
      final s = Sprinkler();
      s.updateWithJson({
        'water_low_alert': 'on',
        'blocked_amount_ml': '250',
      });
      expect(s.waterLowAlert, equals(true));
      expect(s.blockedAmountMl, equals(250));
    });

    test('handles missing fields gracefully', () {
      final s = Sprinkler();
      s.updateWithJson({});
      expect(s.airHumidity, equals(0.0));
      expect(s.airTemperature, equals(0.0));
      expect(s.soilMoisture, equals(0.0));
      expect(s.waterPump, equals('off'));
      expect(s.waterLowAlert, equals(false));
      expect(s.blockedAmountMl, equals(0));
    });

    test('handles null values gracefully', () {
      final s = Sprinkler();
      s.updateWithJson({
        'air_humidity': null,
        'blocked_amount_ml': null,
      });
      expect(s.airHumidity, equals(0.0));
      expect(s.blockedAmountMl, equals(0));
    });

    test('notifies listeners on update', () {
      int notifyCount = 0;
      final s = Sprinkler();
      s.addListener(() {
        notifyCount++;
      });
      s.updateWithJson({'air_temperature': '30.0'});
      expect(notifyCount, equals(1));
    });
  });

  group('Sprinkler blockedAmountMl setter', () {
    test('updates value and notifies', () {
      int notifyCount = 0;
      final s = Sprinkler();
      s.addListener(() {
        notifyCount++;
      });
      s.blockedAmountMl = 500;
      expect(s.blockedAmountMl, equals(500));
      expect(notifyCount, equals(1));
    });
  });
}
