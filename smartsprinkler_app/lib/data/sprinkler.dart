import 'package:flutter/material.dart';

class Sprinkler with ChangeNotifier {
  static final Sprinkler _instance = Sprinkler._(0.0, 0.0, 0.0, "off");

  double _airHumidity;
  double _airTemperature;
  double _soilMoisture;
  String _waterPump;

  double get airHumidity => _airHumidity;
  double get airTemperature => _airTemperature;
  double get soilMoisture => _soilMoisture;
  String get waterPump => _waterPump;

  Sprinkler._(this._airHumidity, this._airTemperature, this._soilMoisture, this._waterPump);

  factory Sprinkler() {
    return _instance;
  }

  void updateWithJson(Map<String, dynamic> json) {
    _instance._airHumidity = double.parse(json['air_humidity'] ?? "0.0");
    _instance._airTemperature = double.parse(json['air_temperature'] ?? "0.0");
    _instance._soilMoisture = double.parse(json['soil_moisture'] ?? "0.0");
    _instance._waterPump = json['water_pump'] ?? "off";

    _instance.notifyListeners();
  }
}