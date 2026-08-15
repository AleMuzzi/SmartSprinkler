import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'settings.dart';

/// Probes the internal (LAN) server URLs and tells [Settings] whether
/// they are reachable. In [UrlMode.auto] this is what decides between the
/// internal and external URL sets — no Wi-Fi SSID / subnet heuristics
/// involved, so it works regardless of platform restrictions.
class NetworkMonitor with ChangeNotifier {
  final Settings _settings = Settings();
  final Connectivity _connectivity = Connectivity();

  static const Duration _probeTimeout = Duration(seconds: 2);
  static const Duration _retryInterval = Duration(seconds: 30);

  StreamSubscription<List<ConnectivityResult>>? _sub;
  Timer? _retryTimer;
  bool _initialised = false;
  bool _internalReachable = false;

  /// Whether the internal URLs were last observed as reachable.
  bool get internalReachable => _internalReachable;

  /// Begin probing. Idempotent — calling twice is a no-op.
  Future<void> start() async {
    if (_initialised) return;
    _initialised = true;

    try {
      _sub = _connectivity.onConnectivityChanged.listen((_) {
        // Network changed (e.g. joined/left Wi-Fi) — re-probe the LAN.
        _probe();
      });
    } catch (e) {
      debugPrint('NetworkMonitor: connectivity stream unavailable: $e');
    }

    _retryTimer = Timer.periodic(_retryInterval, (_) => _probe());

    await _probe();
  }

  void stop() {
    _sub?.cancel();
    _sub = null;
    _retryTimer?.cancel();
    _retryTimer = null;
    _initialised = false;
  }

  Future<void> _probe() async {
    final reachable = await _internalServersReachable();
    debugPrint('NetworkMonitor: internal reachable = $reachable');

    _internalReachable = reachable;
    final changed = _internalReachable != _settings.internalReachable;
    _settings.setInternalReachable(reachable);
    if (changed) notifyListeners();
  }

  /// The internal LAN is reachable when at least one of the configured
  /// internal servers answers. Any HTTP response (even an error status)
  /// proves a route exists — only timeouts / socket errors count as
  /// unreachable.
  Future<bool> _internalServersReachable() async {
    final urls = [
      Uri.parse(_settings.internalEspUrl).replace(path: '/health'),
      Uri.parse(_settings.internalBayesianUrl).replace(path: '/health'),
    ];
    for (final url in urls) {
      try {
        await http.get(url).timeout(_probeTimeout);
        return true;
      } catch (_) {
        // unreachable — try the next server
      }
    }
    return false;
  }
}