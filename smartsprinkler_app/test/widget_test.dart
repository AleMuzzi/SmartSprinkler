import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartsprinkler_app/main.dart';

void main() {
  testWidgets('app renders dashboard with navigation', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartSprinklerApp());
    await tester.pump();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('Dashboard'), findsOneWidget);
    expect(find.text('System'), findsOneWidget);
  });

  testWidgets('system tab shows operational mode controls', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartSprinklerApp());
    await tester.pump();

    await tester.tap(find.text('System'));
    await tester.pumpAndSettle();

    expect(find.text('Operational Mode'), findsOneWidget);
  });
}