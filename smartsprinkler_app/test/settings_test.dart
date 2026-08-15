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

    test('defaults to auto mode and external URLs when unreachable', () {
      final s = Settings();
      expect(s.urlMode, UrlMode.auto);
      s.setInternalReachable(false);
      expect(s.apiUrl, equals('http://my.home.server'));
      expect(s.bayesianUrl, equals('http://my.home.server:8080'));
    });

    test('auto mode returns internal URLs when reachable', () {
      final s = Settings();
      s.setInternalReachable(true);
      expect(s.apiUrl, equals('http://192.168.1.10'));
      expect(s.bayesianUrl, equals('http://192.168.1.7:8080'));
    });
  });

  group('Settings URL mode', () {
    test('forced internal mode ignores reachability', () {
      final s = Settings();
      s.urlMode = UrlMode.internal;
      s.setInternalReachable(false);
      expect(s.apiUrl, equals('http://192.168.1.10'));
      expect(s.bayesianUrl, equals('http://192.168.1.7:8080'));
    });

    test('forced external mode ignores reachability', () {
      final s = Settings();
      s.urlMode = UrlMode.external;
      s.setInternalReachable(true);
      expect(s.apiUrl, equals('http://my.home.server'));
      expect(s.bayesianUrl, equals('http://my.home.server:8080'));
    });
  });

  group('Settings URL updates', () {
    test('apiUrl setter updates internal URL', () {
      final s = Settings();
      s.urlMode = UrlMode.auto;
      s.setInternalReachable(true);
      s.apiUrl = 'http://192.168.1.20';
      expect(s.apiUrl, equals('http://192.168.1.20'));
      // Verify singleton shares state
      final s2 = Settings();
      expect(s2.apiUrl, equals('http://192.168.1.20'));
    });

    test('bayesianUrl setter updates value', () {
      final s = Settings();
      s.urlMode = UrlMode.auto;
      s.setInternalReachable(true);
      s.bayesianUrl = 'http://192.168.1.21:9090';
      expect(s.bayesianUrl, equals('http://192.168.1.21:9090'));
    });

    test('independent URL updates', () {
      final s = Settings();
      s.urlMode = UrlMode.auto;
      s.setInternalReachable(true);
      s.apiUrl = 'http://10.0.0.1';
      s.bayesianUrl = 'http://10.0.0.2:8080';
      expect(s.apiUrl, equals('http://10.0.0.1'));
      expect(s.bayesianUrl, equals('http://10.0.0.2:8080'));
    });

    test('external URLs override when not reachable', () {
      final s = Settings();
      s.setInternalReachable(false);
      expect(s.apiUrl, equals('http://my.home.server'));
      expect(s.bayesianUrl, equals('http://my.home.server:8080'));
    });
  });
}