import 'package:flutter/material.dart';

import '../main.dart';

// Supports all calling styles:
// - showAppToast('message')
// - showAppToast('message', fontSize: 14)
// - showAppToast(message: 'message')
// - showAppToast(msg: 'message')
// - showAppToast(message: 'message', fontSize: 14)
// - showAppToast(msg: 'message', fontSize: 14)
void showAppToast(String message, {Duration duration = const Duration(seconds: 2), int? fontSize}) {
  final context = navigatorKey.currentContext;
  if (context != null) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: fontSize == null ? null : TextStyle(fontSize: fontSize.toDouble()),
        ),
        duration: duration,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}