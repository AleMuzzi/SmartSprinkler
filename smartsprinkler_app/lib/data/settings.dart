import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// How the app decides which URL set to use.
enum UrlMode {
  /// Automatically pick the internal URLs when they are reachable and the
  /// external ones otherwise.
  auto,

  /// Always use the internal (LAN) URLs.
  internal,

  /// Always use the external (public) URLs.
  external,
}

class Settings extends ChangeNotifier {
  static final Settings _instance = Settings._();

  static const String _kInternalEspUrl = 'internal_esp_url';
  static const String _kInternalBayesianUrl = 'internal_bayesian_url';
  static const String _kExternalEspUrl = 'external_esp_url';
  static const String _kExternalBayesianUrl = 'external_bayesian_url';
  static const String _kUrlMode = 'url_mode';

  /// LAN URLs — the app prefers these and falls back to the external ones
  /// when they are unreachable (auto mode).
  String _internalEspUrl = "http://192.168.1.10";
  String _internalBayesianUrl = "http://192.168.1.7:8080";

  /// External URLs (typically a reverse proxy / VPN facing the servers).
  String _externalEspUrl = "http://my.home.server";
  String _externalBayesianUrl = "http://my.home.server:8080";

  /// How the effective URLs are chosen. Defaults to [UrlMode.auto].
  UrlMode _urlMode = UrlMode.auto;

  /// Set by [NetworkMonitor] after probing the LAN. Only consulted in
  /// [UrlMode.auto] mode.
  bool _internalReachable = false;

  bool _loaded = false;

  Settings._();

  factory Settings() {
    return _instance;
  }

  Future<void> load() async {
    if (_loaded) return;
    final prefs = await SharedPreferences.getInstance();
    _internalEspUrl = prefs.getString(_kInternalEspUrl) ?? _internalEspUrl;
    _internalBayesianUrl = prefs.getString(_kInternalBayesianUrl) ?? _internalBayesianUrl;
    _externalEspUrl = prefs.getString(_kExternalEspUrl) ?? _externalEspUrl;
    _externalBayesianUrl =
        prefs.getString(_kExternalBayesianUrl) ?? _externalBayesianUrl;
    final mode = prefs.getString(_kUrlMode);
    _urlMode =
        UrlMode.values.firstWhere((m) => m.name == mode, orElse: () => UrlMode.auto);
    _loaded = true;
  }

  // ── Effective URLs ───────────────────────────────────────────────────

  String get apiUrl => _resolve(_internalEspUrl, _externalEspUrl);
  String get bayesianUrl => _resolve(_internalBayesianUrl, _externalBayesianUrl);

  String _resolve(String internal, String external) {
    switch (_urlMode) {
      case UrlMode.internal:
        return internal;
      case UrlMode.external:
        return external;
      case UrlMode.auto:
        return _internalReachable ? internal : external;
    }
  }

  // Legacy setters — kept so existing call-sites and tests that did
  // ``settings.apiUrl = x`` still compile. They write to the internal URL
  // field (the historical behaviour was "the LAN URL").
  set apiUrl(String url) => internalEspUrl = url;
  set bayesianUrl(String url) => internalBayesianUrl = url;

  UrlMode get urlMode => _urlMode;
  set urlMode(UrlMode mode) {
    if (_urlMode == mode) return;
    _urlMode = mode;
    _persistMode();
    notifyListeners();
  }

  /// Whether the internal LAN URLs were last observed as reachable.
  bool get internalReachable => _internalReachable;

  /// Called by [NetworkMonitor] whenever a LAN probe completes.
  void setInternalReachable(bool value) {
    if (_internalReachable == value) return;
    _internalReachable = value;
    if (_urlMode == UrlMode.auto) notifyListeners();
  }

  // ── Per-network URL setters (always write the matching field) ────────

  String get internalEspUrl => _internalEspUrl;
  set internalEspUrl(String url) {
    _internalEspUrl = url;
    _persist(_kInternalEspUrl, url);
    notifyListeners();
  }

  String get internalBayesianUrl => _internalBayesianUrl;
  set internalBayesianUrl(String url) {
    _internalBayesianUrl = url;
    _persist(_kInternalBayesianUrl, url);
    notifyListeners();
  }

  String get externalEspUrl => _externalEspUrl;
  set externalEspUrl(String url) {
    _externalEspUrl = url;
    _persist(_kExternalEspUrl, url);
    notifyListeners();
  }

  String get externalBayesianUrl => _externalBayesianUrl;
  set externalBayesianUrl(String url) {
    _externalBayesianUrl = url;
    _persist(_kExternalBayesianUrl, url);
    notifyListeners();
  }

  Future<void> _persist(String key, String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, value);
  }

  Future<void> _persistMode() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUrlMode, _urlMode.name);
  }
}