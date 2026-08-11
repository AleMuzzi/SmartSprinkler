import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'water_alert_service.dart';

class Sprinkler with ChangeNotifier {
  static final Sprinkler _instance = Sprinkler._(0.0, 0.0, 0.0, "off", false, 0, null, null, 0.0, 0.0);

  double _airHumidity;
  double _airTemperature;
  double _soilMoisture;
  String _waterPump;
  bool _waterLowAlert;
  int _blockedAmountMl;
  int? _rotaryPosition;
  String? _activePlant;
  // Cistern tracking. Updated by the Bayesian server via /api/cistern.
  // Both values default to 0 (unknown) and are populated by the first
  // successful /api/cistern response — see ``_cisternDataReceived`` below.
  double _cisternLevelMl;
  double _cisternCapacityMl;
  bool _cisternDataReceived = false;
  // Weather values reported by the Bayesian server (/api/weather/status).
  // These override the ESP values once received so the UI shows the
  // server-side merged reading rather than the raw ESP payload (which can
  // be stale or hardcoded by the mock ESP).
  double? _serverTempC;
  double? _serverHumidityPct;
  bool _weatherFromServerReceived = false;

  double get airHumidity => _weatherFromServerReceived ? _serverHumidityPct! : _airHumidity;
  double get airTemperature => _weatherFromServerReceived ? _serverTempC! : _airTemperature;
  double get soilMoisture => _soilMoisture;
  String get waterPump => _waterPump;
  bool get waterLowAlert => _waterLowAlert;
  int get blockedAmountMl => _blockedAmountMl;
  int? get rotaryPosition => _rotaryPosition;
  String? get activePlant => _activePlant;
  double get cisternLevelMl => _cisternLevelMl;
  double get cisternCapacityMl => _cisternCapacityMl;
  bool get cisternDataReceived => _cisternDataReceived;
  double get cisternLevelPct =>
      (_cisternDataReceived && _cisternCapacityMl > 0)
          ? (_cisternLevelMl / _cisternCapacityMl) * 100.0
          : 0.0;
  bool get weatherFromServerReceived => _weatherFromServerReceived;
  double? get serverTempC => _serverTempC;
  double? get serverHumidityPct => _serverHumidityPct;

  set blockedAmountMl(int value) {
    _blockedAmountMl = value;
    notifyListeners();
  }

  Sprinkler._(this._airHumidity, this._airTemperature, this._soilMoisture, this._waterPump,
              this._waterLowAlert, this._blockedAmountMl, this._rotaryPosition, this._activePlant,
              this._cisternLevelMl, this._cisternCapacityMl);

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

  void updateCisternWithJson(Map<String, dynamic> json) {
    _instance._cisternLevelMl = _parseDoubleOrNan(json['level_ml']);
    _instance._cisternCapacityMl = _parseDoubleOrNan(json['capacity_ml']);
    _instance._cisternDataReceived = true;
    final serverAlert = json['water_low_alert'] == true;
    if (serverAlert != _instance._waterLowAlert) {
      _instance._waterLowAlert = serverAlert;
      // Persist last-known state so the in-app banner reflects it on cold start.
      WaterAlertService.setLastAlertState(serverAlert);
    }
    _instance.notifyListeners();
  }

  void updateWeatherFromServer(Map<String, dynamic> json) {
    final t = _parseDoubleOrNan(json['temperature']);
    final h = _parseDoubleOrNan(json['humidity']);
    if (t == 0.0 && h == 0.0) return; // ignore empty payloads
    _instance._serverTempC = t;
    _instance._serverHumidityPct = h;
    _instance._weatherFromServerReceived = true;
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