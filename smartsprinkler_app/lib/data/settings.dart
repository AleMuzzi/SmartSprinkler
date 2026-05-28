class Settings {
  static final Settings _instance = Settings._();

  String apiBaseUrl = "http://192.168.1.10";
  String bayesianServerUrl = "http://192.168.1.7:8080";

  Settings._();

  factory Settings() {
    return _instance;
  }

  String get apiUrl => _instance.apiBaseUrl;
  set apiUrl(String url) {
    _instance.apiBaseUrl = url;
  }

  String get bayesianUrl => _instance.bayesianServerUrl;
  set bayesianUrl(String url) {
    _instance.bayesianServerUrl = url;
  }
}