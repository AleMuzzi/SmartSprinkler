import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'water_alert_service.dart';

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

  Future<void> restoreWaterAlertState() async {
    final lastAlert = await WaterAlertService.getLastAlertState();
    if (lastAlert != _waterLowAlert) {
      _waterLowAlert = lastAlert;
      notifyListeners();
    }
  }

  void updateWithJson(Map<String, dynamic> json) {
    _instance._airHumidity = _parseDoubleOrNan(json['air_humidity']);
    _instance._airTemperature = _parseDoubleOrNan(json['air_temperature']);
    _instance._soilMoisture = _parseDoubleOrNan(json['soil_moisture']);
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

  double _parseDoubleOrNan(dynamic value) {
    if (value == null) return 0.0;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) {
      if (value == 'nan' || value == 'null' || value.isEmpty) return 0.0;
      return double.tryParse(value) ?? 0.0;
    }
    return 0.0;
  }
}