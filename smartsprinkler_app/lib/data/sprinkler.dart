import 'package:flutter/material.dart';

class Sprinkler with ChangeNotifier {
  static final Sprinkler _instance = Sprinkler._(0.0, 0.0, 0.0, "off", false, 0, null, null);

  double _airHumidity;
  double _airTemperature;
  double _soilMoisture;
  String _waterPump;
  bool _waterLowAlert;
  int _blockedAmountMl;
  int? _rotaryPosition;
  String? _activePlant;

  double get airHumidity => _airHumidity;
  double get airTemperature => _airTemperature;
  double get soilMoisture => _soilMoisture;
  String get waterPump => _waterPump;
  bool get waterLowAlert => _waterLowAlert;
  int get blockedAmountMl => _blockedAmountMl;
  int? get rotaryPosition => _rotaryPosition;
  String? get activePlant => _activePlant;

  set blockedAmountMl(int value) {
    _blockedAmountMl = value;
    notifyListeners();
  }

  Sprinkler._(this._airHumidity, this._airTemperature, this._soilMoisture, this._waterPump,
              this._waterLowAlert, this._blockedAmountMl, this._rotaryPosition, this._activePlant);

  factory Sprinkler() {
    return _instance;
  }

  void updateWithJson(Map<String, dynamic> json) {
    _instance._airHumidity = double.parse(json['air_humidity'] ?? "0.0");
    _instance._airTemperature = double.parse(json['air_temperature'] ?? "0.0");
    _instance._soilMoisture = double.parse(json['soil_moisture'] ?? "0.0");
    _instance._waterPump = json['water_pump'] ?? "off";
    _instance._waterLowAlert = json['water_low_alert'] == "on";
    _instance._blockedAmountMl = int.tryParse(json['blocked_amount_ml'] ?? "0") ?? 0;
    _instance._activePlant = json['active_plant'] == "null" ? null : json['active_plant'];

    final posStr = json['rotary_position'];
    if (posStr == "uncalibrated" || posStr == null) {
      _instance._rotaryPosition = null;
    } else {
      _instance._rotaryPosition = int.tryParse(posStr.toString());
    }

    _instance.notifyListeners();
  }
}