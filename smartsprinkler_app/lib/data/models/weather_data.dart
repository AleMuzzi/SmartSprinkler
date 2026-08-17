class WeatherData {
  final double? temperature;
  final double? humidity;
  final String cloudCover;
  final String rainForecast;
  // Provenance of each reading: "esp" (measured on-site by the DHT) or
  // "web" (server fell back to the forecast because the ESP reported -1).
  final String temperatureSource;
  final String humiditySource;
  final DateTime fetchedAt;

  WeatherData({
    required this.temperature,
    required this.humidity,
    required this.cloudCover,
    required this.rainForecast,
    this.temperatureSource = 'esp',
    this.humiditySource = 'esp',
    DateTime? fetchedAt,
  }) : fetchedAt = fetchedAt ?? DateTime.now();

  factory WeatherData.fromJson(Map<String, dynamic> json) {
    return WeatherData(
      temperature: (json['temperature'] as num?)?.toDouble(),
      humidity: (json['humidity'] as num?)?.toDouble(),
      cloudCover: json['cloud_cover'] ?? 'unknown',
      rainForecast: json['rain_forecast'] ?? 'unknown',
      temperatureSource: (json['temperature_source'] as String?) ?? 'esp',
      humiditySource: (json['humidity_source'] as String?) ?? 'esp',
    );
  }
}

enum ConnectivityStatus {
  connected,
  disconnected,
  checking,
}