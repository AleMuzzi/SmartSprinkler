import 'package:shared_preferences/shared_preferences.dart';

class Settings {
  static final Settings _instance = Settings._();

  static const String _kEspUrl = 'esp_url';
  static const String _kBayesianUrl = 'bayesian_url';

  String apiBaseUrl = "http://192.168.1.10";
  String bayesianServerUrl = "http://192.168.1.7:8080";

  bool _loaded = false;

  Settings._();

  factory Settings() {
    return _instance;
  }

  Future<void> load() async {
    if (_loaded) return;
    final prefs = await SharedPreferences.getInstance();
    apiBaseUrl = prefs.getString(_kEspUrl) ?? apiBaseUrl;
    bayesianServerUrl = prefs.getString(_kBayesianUrl) ?? bayesianServerUrl;
    _loaded = true;
  }

  String get apiUrl => _instance.apiBaseUrl;
  set apiUrl(String url) {
    _instance.apiBaseUrl = url;
    _persist(_kEspUrl, url);
  }

  String get bayesianUrl => _instance.bayesianServerUrl;
  set bayesianUrl(String url) {
    _instance.bayesianServerUrl = url;
    _persist(_kBayesianUrl, url);
  }

  Future<void> _persist(String key, String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, value);
  }
}