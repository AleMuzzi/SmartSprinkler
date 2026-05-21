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

enum OperationMode {
  automatic,
  manual,
  scheduled,
}

extension OperationModeExtension on OperationMode {
  String get displayName {
    switch (this) {
      case OperationMode.automatic:
        return 'Automatic (Bayesian)';
      case OperationMode.manual:
        return 'Manual';
      case OperationMode.scheduled:
        return 'Scheduled';
    }
  }

  String get description {
    switch (this) {
      case OperationMode.automatic:
        return 'Watering decisions made by Bayesian server';
      case OperationMode.manual:
        return 'Direct ESP control, no logging';
      case OperationMode.scheduled:
        return 'Time-based watering schedule';
    }
  }
}

enum ConnectivityStatus {
  connected,
  disconnected,
  checking,
}