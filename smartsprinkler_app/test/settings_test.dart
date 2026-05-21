import 'package:flutter_test/flutter_test.dart';
import 'package:smartsprinkler_app/data/settings.dart';

void main() {
  group('Settings singleton', () {
    test('returns same instance', () {
      final s1 = Settings();
      final s2 = Settings();
      expect(identical(s1, s2), isTrue);
    });

    test('has default API URL', () {
      final s = Settings();
      expect(s.apiUrl, equals('http://192.168.1.10'));
    });

    test('has default Bayesian URL', () {
      final s = Settings();
      expect(s.bayesianUrl, equals('http://192.168.1.11:8080'));
    });
  });

  group('Settings URL updates', () {
    test('apiUrl setter updates value', () {
      final s = Settings();
      s.apiUrl = 'http://192.168.1.20';
      expect(s.apiUrl, equals('http://192.168.1.20'));
      // Verify singleton shares state
      final s2 = Settings();
      expect(s2.apiUrl, equals('http://192.168.1.20'));
    });

    test('bayesianUrl setter updates value', () {
      final s = Settings();
      s.bayesianUrl = 'http://192.168.1.21:9090';
      expect(s.bayesianUrl, equals('http://192.168.1.21:9090'));
    });

    test('independent URL updates', () {
      final s = Settings();
      s.apiUrl = 'http://10.0.0.1';
      s.bayesianUrl = 'http://10.0.0.2:8080';
      expect(s.apiUrl, equals('http://10.0.0.1'));
      expect(s.bayesianUrl, equals('http://10.0.0.2:8080'));
    });
  });
}
