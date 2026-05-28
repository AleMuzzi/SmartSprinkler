class WeatherData {
  final double temperature;
  final double humidity;
  final String cloudCover;
  final String rainForecast;
  final DateTime fetchedAt;

  WeatherData({
    required this.temperature,
    required this.humidity,
    required this.cloudCover,
    required this.rainForecast,
    DateTime? fetchedAt,
  }) : fetchedAt = fetchedAt ?? DateTime.now();

  factory WeatherData.fromJson(Map<String, dynamic> json) {
    return WeatherData(
      temperature: (json['temperature'] ?? 0.0).toDouble(),
      humidity: (json['humidity'] ?? 0.0).toDouble(),
      cloudCover: json['cloud_cover'] ?? 'unknown',
      rainForecast: json['rain_forecast'] ?? 'unknown',
    );
  }
}

enum ConnectivityStatus {
  connected,
  disconnected,
  checking,
}