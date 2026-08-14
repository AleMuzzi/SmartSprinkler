import 'package:shared_preferences/shared_preferences.dart';

class Settings {
  static final Settings _instance = Settings._();

  static const String _kInternalEspUrl = 'internal_esp_url';
  static const String _kInternalBayesianUrl = 'internal_bayesian_url';
  static const String _kExternalEspUrl = 'external_esp_url';
  static const String _kExternalBayesianUrl = 'external_bayesian_url';
  static const String _kHomeWifiSsid = 'home_wifi_ssid';

  /// LAN URLs (used when the phone is connected to the home Wi-Fi).
  String _internalEspUrl = "http://192.168.1.10";
  String _internalBayesianUrl = "http://192.168.1.7:8080";

  /// External URLs (used when the phone is on cellular or away from home).
  String _externalEspUrl = "http://my.home.server";
  String _externalBayesianUrl = "http://my.home.server:8080";

  /// SSID of the home Wi-Fi. When the device is connected to this network
  /// the app transparently switches to the internal URLs.
  String? _homeWifiSsid;

  /// Set by NetworkMonitor when the connection state changes. When true,
  /// getters return the internal URLs; otherwise the external ones.
  bool _connectedToHomeWifi = false;

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
    _homeWifiSsid = prefs.getString(_kHomeWifiSsid);
    _loaded = true;
  }

  // ── Effective URLs (depend on the current connection) ───────────────

  String get apiUrl => _connectedToHomeWifi ? _internalEspUrl : _externalEspUrl;
  String get bayesianUrl =>
      _connectedToHomeWifi ? _internalBayesianUrl : _externalBayesianUrl;

  // Legacy setters — kept so existing call-sites and tests that did
  // ``settings.apiUrl = x`` still compile. They write to the internal URL
  // field (the historical behaviour was "the LAN URL").
  set apiUrl(String url) => internalEspUrl = url;
  set bayesianUrl(String url) => internalBayesianUrl = url;

  bool get connectedToHomeWifi => _connectedToHomeWifi;

  /// Called by [NetworkMonitor] whenever the connection state changes.
  void setConnectedToHomeWifi(bool value) {
    if (_connectedToHomeWifi == value) return;
    _connectedToHomeWifi = value;
  }

  // ── Per-network URL setters (always write the matching field) ────────

  String get internalEspUrl => _internalEspUrl;
  set internalEspUrl(String url) {
    _internalEspUrl = url;
    _persist(_kInternalEspUrl, url);
  }

  String get internalBayesianUrl => _internalBayesianUrl;
  set internalBayesianUrl(String url) {
    _internalBayesianUrl = url;
    _persist(_kInternalBayesianUrl, url);
  }

  String get externalEspUrl => _externalEspUrl;
  set externalEspUrl(String url) {
    _externalEspUrl = url;
    _persist(_kExternalEspUrl, url);
  }

  String get externalBayesianUrl => _externalBayesianUrl;
  set externalBayesianUrl(String url) {
    _externalBayesianUrl = url;
    _persist(_kExternalBayesianUrl, url);
  }

  String? get homeWifiSsid => _homeWifiSsid;
  set homeWifiSsid(String? ssid) {
    _homeWifiSsid = (ssid != null && ssid.isEmpty) ? null : ssid;
    _persist(_kHomeWifiSsid, _homeWifiSsid);
  }

  Future<void> _persist(String key, String? value) async {
    final prefs = await SharedPreferences.getInstance();
    if (value == null) {
      await prefs.remove(key);
    } else {
      await prefs.setString(key, value);
    }
  }
}