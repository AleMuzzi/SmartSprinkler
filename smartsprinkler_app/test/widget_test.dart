import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smartsprinkler_app/main.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<void> pumpApp(WidgetTester tester) async {
    await tester.pumpWidget(const SmartSprinklerApp());
    await tester.pump();
    for (var i = 0; i < 50 && find.byType(NavigationBar).evaluate().isEmpty; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
  }

  testWidgets('app renders dashboard with navigation', (WidgetTester tester) async {
    await pumpApp(tester);

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('Dashboard'), findsOneWidget);
    expect(find.text('System'), findsOneWidget);
  });

  testWidgets('system tab shows operational mode controls', (WidgetTester tester) async {
    await pumpApp(tester);

    await tester.tap(find.text('System'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('Servizio di inferenza'), findsOneWidget);
  });
}
