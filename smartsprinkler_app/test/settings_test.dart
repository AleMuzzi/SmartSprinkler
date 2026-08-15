import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smartsprinkler_app/data/settings.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Settings singleton', () {
    test('returns same instance', () {
      final s1 = Settings();
      final s2 = Settings();
      expect(identical(s1, s2), isTrue);
    });

    test('has default external URLs when not connected to home', () {
      final s = Settings();
      s.setConnectedToHomeWifi(false);
      expect(s.apiUrl, equals('http://my.home.server'));
      expect(s.bayesianUrl, equals('http://my.home.server:8080'));
    });

    test('has default internal URLs when connected to home', () {
      final s = Settings();
      s.setConnectedToHomeWifi(true);
      expect(s.apiUrl, equals('http://192.168.1.10'));
      expect(s.bayesianUrl, equals('http://192.168.1.7:8080'));
    });
  });

  group('Settings URL updates', () {
    test('apiUrl setter updates internal URL', () {
      final s = Settings();
      s.setConnectedToHomeWifi(true);
      s.apiUrl = 'http://192.168.1.20';
      expect(s.apiUrl, equals('http://192.168.1.20'));
      // Verify singleton shares state
      final s2 = Settings();
      expect(s2.apiUrl, equals('http://192.168.1.20'));
    });

    test('bayesianUrl setter updates value', () {
      final s = Settings();
      s.setConnectedToHomeWifi(true);
      s.bayesianUrl = 'http://192.168.1.21:9090';
      expect(s.bayesianUrl, equals('http://192.168.1.21:9090'));
    });

    test('independent URL updates', () {
      final s = Settings();
      s.setConnectedToHomeWifi(true);
      s.apiUrl = 'http://10.0.0.1';
      s.bayesianUrl = 'http://10.0.0.2:8080';
      expect(s.apiUrl, equals('http://10.0.0.1'));
      expect(s.bayesianUrl, equals('http://10.0.0.2:8080'));
    });

    test('external URLs override when not connected to home', () {
      final s = Settings();
      s.setConnectedToHomeWifi(false);
      expect(s.apiUrl, equals('http://my.home.server'));
      expect(s.bayesianUrl, equals('http://my.home.server:8080'));
    });
  });
}