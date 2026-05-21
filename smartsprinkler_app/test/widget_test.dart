import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartsprinkler_app/main.dart';

void main() {
  testWidgets('app renders home page with irrigation buttons', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pump();

    expect(find.text('Start Irrigation'), findsOneWidget);
    expect(find.text('Stop Irrigation'), findsOneWidget);
  });

  testWidgets('drawer has Home and Settings pages', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pump();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();

    expect(find.text('Smart Sprinkler'), findsOneWidget);
    expect(find.text('🏠 Home'), findsOneWidget);
    expect(find.text('⚙️ Settings'), findsOneWidget);
  });

  testWidgets('tapping Settings navigates to settings page', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pump();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();

    await tester.tap(find.text('⚙️ Settings'));
    await tester.pumpAndSettle();

    expect(find.text('Sprinkler settings'), findsOneWidget);
    expect(find.text('ESP Sprinkler URL'), findsOneWidget);
    expect(find.text('Bayesian Server URL'), findsOneWidget);
  });
}
