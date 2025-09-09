class Settings {
  // Singleton instance
  static final Settings _instance = Settings._();

  // String apiBaseUrl = "http://sprinkler.casabrignuzzi.com.es";
  String apiBaseUrl = "http://192.168.1.10";

  // Private constructor to prevent direct instantiation
  Settings._();

  // Factory constructor to return the singleton instance
  factory Settings() {
    return _instance;
  }

  String get apiUrl => _instance.apiBaseUrl;
  set apiUrl(String url) {
    _instance.apiBaseUrl = url;
  }
}