import 'package:flutter_test/flutter_test.dart';
import 'package:smartsprinkler_app/model/command.dart';

void main() {
  group('Action enum', () {
    test('has STOP as index 0', () {
      expect(Action.STOP.index, equals(0));
    });

    test('has START as index 1', () {
      expect(Action.START.index, equals(1));
    });

    test('has DISPENSE_SPECIFIC_AMOUNT as index 2', () {
      expect(Action.DISPENSE_SPECIFIC_AMOUNT.index, equals(2));
    });

    test('values match firmware C++ Action enum', () {
      expect(Action.values.length, equals(3));
    });
  });

  group('Target enum', () {
    test('has NAGA_MORICH as index 0', () {
      expect(Target.NAGA_MORICH.index, equals(0));
    });

    test('has ROSMARINO as index 1', () {
      expect(Target.ROSMARINO.index, equals(1));
    });

    test('has HABANERO as index 2', () {
      expect(Target.HABANERO.index, equals(2));
    });

    test('has CAROLINA_REAPER as index 3', () {
      expect(Target.CAROLINA_REAPER.index, equals(3));
    });

    test('values match firmware C++ Target enum', () {
      expect(Target.values.length, equals(4));
    });
  });

  group('Command', () {
    test('creates START command with default values', () {
      final cmd = Command(action: Action.START, target: Target.NAGA_MORICH);
      expect(cmd.action, equals(Action.START));
      expect(cmd.target, equals(Target.NAGA_MORICH));
      expect(cmd.amount, equals(0));
      expect(cmd.force, equals(false));
    });

    test('creates DISPENSE command with amount', () {
      final cmd = Command(
        action: Action.DISPENSE_SPECIFIC_AMOUNT,
        target: Target.HABANERO,
        amount: 250,
      );
      expect(cmd.action, equals(Action.DISPENSE_SPECIFIC_AMOUNT));
      expect(cmd.target, equals(Target.HABANERO));
      expect(cmd.amount, equals(250));
      expect(cmd.force, equals(false));
    });

    test('creates command with force flag', () {
      final cmd = Command(
        action: Action.START,
        target: Target.ROSMARINO,
        force: true,
      );
      expect(cmd.force, equals(true));
    });

    test('toJson returns correct JSON string', () {
      final cmd = Command(
        action: Action.START,
        target: Target.NAGA_MORICH,
        amount: 0,
        force: false,
      );
      final json = cmd.toJson();
      expect(json, contains('"action": "START"'));
      expect(json, contains('"target": "NAGA_MORICH"'));
      expect(json, contains('"amount": 0'));
      expect(json, contains('"force": false'));
    });

    test('toJson with all fields set', () {
      final cmd = Command(
        action: Action.DISPENSE_SPECIFIC_AMOUNT,
        target: Target.CAROLINA_REAPER,
        amount: 500,
        force: true,
      );
      final json = cmd.toJson();
      expect(json, contains('"action": "DISPENSE_SPECIFIC_AMOUNT"'));
      expect(json, contains('"target": "CAROLINA_REAPER"'));
      expect(json, contains('"amount": 500'));
      expect(json, contains('"force": true'));
    });

    test('name values match firmware Target::from_string expectations', () {
      expect(Target.NAGA_MORICH.name, equals('NAGA_MORICH'));
      expect(Target.ROSMARINO.name, equals('ROSMARINO'));
      expect(Target.HABANERO.name, equals('HABANERO'));
      expect(Target.CAROLINA_REAPER.name, equals('CAROLINA_REAPER'));
    });

    test('Action names match firmware Action::from_string expectations', () {
      expect(Action.STOP.name, equals('STOP'));
      expect(Action.START.name, equals('START'));
      expect(Action.DISPENSE_SPECIFIC_AMOUNT.name, equals('DISPENSE_SPECIFIC_AMOUNT'));
    });
  });
}
