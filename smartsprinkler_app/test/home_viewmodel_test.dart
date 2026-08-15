import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

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

    test('settings has default external values', () {
      final vm = HomePageViewModel();
      vm.settings.setInternalReachable(false);
      expect(vm.settings.apiUrl, equals('http://my.home.server'));
      expect(vm.settings.bayesianUrl, equals('http://my.home.server:8080'));
    });
  });
}