import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:network_info_plus/network_info_plus.dart';

import 'settings.dart';

/// Watches the device's network state and tells [Settings] whether the
/// current connection matches the configured home Wi-Fi. When it does,
/// the app uses the *internal* server URLs; otherwise the *external*
/// ones (typically a reverse proxy / VPN).
class NetworkMonitor with ChangeNotifier {
  final Settings _settings = Settings();
  final Connectivity _connectivity = Connectivity();
  final NetworkInfo _networkInfo = NetworkInfo();

  StreamSubscription<List<ConnectivityResult>>? _sub;
  bool _initialised = false;
  String? _currentSsid;
  bool _currentIsHomeWifi = false;

  /// Most recently observed Wi-Fi SSID (stripped of any surrounding
  /// quotes Android sometimes adds). `null` when not on Wi-Fi.
  String? get currentSsid => _currentSsid;

  /// Whether [Settings] is currently routing through the internal URLs.
  bool get isHomeWifi => _currentIsHomeWifi;

  /// Begin listening. Idempotent — calling twice is a no-op.
  Future<void> start() async {
    if (_initialised) return;
    _initialised = true;
    try {
      _sub = _connectivity.onConnectivityChanged.listen(_onChange);
    } catch (e) {
      debugPrint('NetworkMonitor: connectivity stream unavailable: $e');
    }
    // Seed with the current connectivity state.
    try {
      final initial = await _connectivity.checkConnectivity();
      await _onChange(initial);
    } catch (e) {
      debugPrint('NetworkMonitor: checkConnectivity failed: $e');
    }
  }

  void stop() {
    _sub?.cancel();
    _sub = null;
    _initialised = false;
  }

  Future<void> _onChange(List<ConnectivityResult> results) async {
    final onWifi = results.contains(ConnectivityResult.wifi) &&
        !results.contains(ConnectivityResult.none);

    String? ssid;
    if (onWifi) {
      try {
        ssid = await _networkInfo.getWifiName();
      } catch (e) {
        debugPrint('NetworkMonitor: getWifiName failed: $e');
      }
    }
    ssid = _cleanSsid(ssid);

    final homeSsid = _settings.homeWifiSsid;
    final isHome = onWifi && homeSsid != null && homeSsid.isNotEmpty
        && ssid == homeSsid;

    final changed = ssid != _currentSsid || isHome != _currentIsHomeWifi;
    _currentSsid = ssid;
    _currentIsHomeWifi = isHome;
    _settings.setConnectedToHomeWifi(isHome);
    if (changed) notifyListeners();
  }

  /// Android wraps the SSID in quotes ("MyWiFi") — normalise that out
  /// and trim whitespace.
  static String? _cleanSsid(String? raw) {
    if (raw == null) return null;
    var s = raw.trim();
    if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
      s = s.substring(1, s.length - 1);
    }
    return s.isEmpty ? null : s;
  }
}