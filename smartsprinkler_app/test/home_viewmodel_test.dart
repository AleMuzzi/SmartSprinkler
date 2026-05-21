import 'package:flutter_test/flutter_test.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';

void main() {
  group('HomePageViewModel', () {
    test('initial notifyBayesian is true', () {
      final vm = HomePageViewModel();
      expect(vm.notifyBayesian, isTrue);
    });

    test('notifyBayesian can be toggled', () {
      final vm = HomePageViewModel();
      vm.notifyBayesian = false;
      expect(vm.notifyBayesian, isFalse);
      vm.notifyBayesian = true;
      expect(vm.notifyBayesian, isTrue);
    });

    test('settings has default values', () {
      final vm = HomePageViewModel();
      expect(vm.settings.apiUrl, equals('http://192.168.1.10'));
      expect(vm.settings.bayesianUrl, equals('http://192.168.1.11:8080'));
    });
  });
}
