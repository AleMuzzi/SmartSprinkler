import 'dart:async';
import 'dart:convert';
import 'dart:developer';

import 'package:flutter/material.dart' hide Action;
import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/data/settings.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';
import 'package:smartsprinkler_app/data/models/plant_data.dart';
import 'package:smartsprinkler_app/data/models/weather_data.dart';
import 'package:smartsprinkler_app/model/command.dart';
import 'package:fluttertoast/fluttertoast.dart';

class DashboardViewModel extends ChangeNotifier {
  final Settings settings = Settings();
  final Sprinkler sprinkler = Sprinkler();

  Timer? _espTimer;
  Timer? _bayesianTimer;

  List<PlantData> _plants = [];
  List<BayesianPlantStatus> _plantStatuses = [];
  double _averageProbabilityOfNeed = 0.0;
  OperationMode _operationMode = OperationMode.automatic;
  WeatherData? _weather;
  ConnectivityStatus _espStatus = ConnectivityStatus.checking;
  ConnectivityStatus _bayesianStatus = ConnectivityStatus.checking;

  List<PlantData> get plants => _plants;
  List<BayesianPlantStatus> get plantStatuses => _plantStatuses;
  double get averageProbabilityOfNeed => _averageProbabilityOfNeed;
  OperationMode get operationMode => _operationMode;
  WeatherData? get weather => _weather;
  ConnectivityStatus get espStatus => _espStatus;
  ConnectivityStatus get bayesianStatus => _bayesianStatus;

  DashboardViewModel() {
    _initDefaultPlants();
    _startPolling();
  }

  void _initDefaultPlants() {
    _plants = [
      PlantData(
        id: 'habanero',
        displayName: 'Habanero',
        imageUrl: 'assets/images/habanero.jpg',
        target: Target.HABANERO,
      ),
      PlantData(
        id: 'naga_morich',
        displayName: 'Naga Morich',
        imageUrl: 'assets/images/naga_morich.jpg',
        target: Target.NAGA_MORICH,
      ),
      PlantData(
        id: 'carolina_reaper',
        displayName: 'Carolina Reaper',
        imageUrl: 'assets/images/carolina_reaper.jpg',
        target: Target.CAROLINA_REAPER,
      ),
      PlantData(
        id: 'rosmarino',
        displayName: 'Rosmarino',
        imageUrl: 'assets/images/rosmarino.jpg',
        target: Target.ROSMARINO,
      ),
    ];
  }

  void _startPolling() {
    _fetchEspStatus();
    _fetchBayesianStatus();
    _checkConnectivity();

    _espTimer = Timer.periodic(const Duration(seconds: 5), (_) => _fetchEspStatus());
    _bayesianTimer = Timer.periodic(const Duration(seconds: 30), (_) => _fetchBayesianStatus());
    Timer.periodic(const Duration(seconds: 30), (_) => _checkConnectivity());
  }

  @override
  void dispose() {
    _espTimer?.cancel();
    _bayesianTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchEspStatus() async {
    try {
      final response = await http.get(
        Uri.parse('${settings.apiUrl}/status'),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        sprinkler.updateWithJson(json);

        if (json['soil_moisture_0'] != null) {
          _updatePlantSoilMoisture(0, _parseDouble(json['soil_moisture_0']));
        }
        if (json['soil_moisture_1'] != null) {
          _updatePlantSoilMoisture(1, _parseDouble(json['soil_moisture_1']));
        }
        if (json['soil_moisture_2'] != null) {
          _updatePlantSoilMoisture(2, _parseDouble(json['soil_moisture_2']));
        }
        if (json['soil_moisture_3'] != null) {
          _updatePlantSoilMoisture(3, _parseDouble(json['soil_moisture_3']));
        }

        final activePlant = json['active_plant'];
        if (activePlant != null && activePlant != 'null') {
          for (var plant in _plants) {
            plant.isWatering = plant.target.name == activePlant;
          }
        } else {
          for (var plant in _plants) {
            plant.isWatering = false;
          }
        }

        _espStatus = ConnectivityStatus.connected;
        notifyListeners();
      }
    } catch (e) {
      log('ESP status fetch error: $e');
      _espStatus = ConnectivityStatus.disconnected;
      notifyListeners();
    }
  }

  void _updatePlantSoilMoisture(int index, double moisture) {
    if (index < _plants.length) {
      _plants[index].soilMoisture = moisture.clamp(0, 100);
      _plants[index].rotaryPosition = index;
    }
  }

  double _parseDouble(dynamic value) {
    if (value == null) return 0.0;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }

  Future<void> _fetchBayesianStatus() async {
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/plants/status'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        _weather = WeatherData.fromJson(json['weather'] ?? {});

        final plantsJson = json['plants'] as List<dynamic>? ?? [];
        _plantStatuses = plantsJson.map((p) => BayesianPlantStatus.fromJson(p)).toList();

        double sum = 0;
        int count = 0;
        for (final status in _plantStatuses) {
          final plant = _plants.firstWhere(
            (pl) => pl.id == status.plantId || pl.target.name.toLowerCase() == status.plantId.toLowerCase(),
            orElse: () => PlantData(id: '', displayName: '', imageUrl: '', target: Target.NAGA_MORICH),
          );
          plant.probabilityOfNeed = status.probabilityOfNeed;
          sum += status.probabilityOfNeed;
          count++;
        }
        _averageProbabilityOfNeed = count > 0 ? sum / count : 0.0;

        _bayesianStatus = ConnectivityStatus.connected;
        notifyListeners();
      }
    } catch (e) {
      log('Bayesian status fetch error: $e');
      _bayesianStatus = ConnectivityStatus.disconnected;
      notifyListeners();
    }
  }

  Future<void> _checkConnectivity() async {
    checkEspConnectivity();
    checkBayesianConnectivity();
  }

  Future<void> checkEspConnectivity() async {
    try {
      final response = await http.get(
        Uri.parse('${settings.apiUrl}/health'),
      ).timeout(const Duration(seconds: 3));
      _espStatus = response.statusCode == 200
          ? ConnectivityStatus.connected
          : ConnectivityStatus.disconnected;
    } catch (e) {
      _espStatus = ConnectivityStatus.disconnected;
    }
    notifyListeners();
  }

  Future<void> checkBayesianConnectivity() async {
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/health'),
      ).timeout(const Duration(seconds: 3));
      _bayesianStatus = response.statusCode == 200
          ? ConnectivityStatus.connected
          : ConnectivityStatus.disconnected;
    } catch (e) {
      _bayesianStatus = ConnectivityStatus.disconnected;
    }
    notifyListeners();
  }

  void setOperationMode(OperationMode mode) {
    _operationMode = mode;
    notifyListeners();
  }

  Future<void> waterPlantNow(PlantData plant) async {
    if (_operationMode == OperationMode.manual) {
      await _waterDirect(plant);
    } else {
      final success = await _waterViaBayesian(plant);
      if (!success && _bayesianStatus == ConnectivityStatus.disconnected) {
        await _waterDirect(plant);
        await Fluttertoast.showToast(
          msg: '⚠️ Bayesian offline — watered ${plant.displayName} directly via ESP',
          fontSize: 14,
        );
      }
    }
  }

  Future<void> _waterDirect(PlantData plant) async {
    try {
      final response = await http.post(
        Uri.parse('${settings.apiUrl}/command'),
        body: Command(target: plant.target, action: Action.START).toJson(),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        await Fluttertoast.showToast(msg: '✅ ${plant.displayName} watering started', fontSize: 16);
      } else {
        await Fluttertoast.showToast(msg: '❌ ESP error: ${response.statusCode}', fontSize: 16);
      }
    } catch (e) {
      await Fluttertoast.showToast(msg: '❌ ESP unreachable', fontSize: 16);
    }
  }

  Future<bool> _waterViaBayesian(PlantData plant) async {
    try {
      final payload = jsonEncode({'plant_type': plant.id});
      final response = await http.post(
        Uri.parse('${settings.bayesianUrl}/api/plants/manual-water'),
        headers: {'Content-Type': 'application/json'},
        body: payload,
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        await Fluttertoast.showToast(msg: '✅ ${plant.displayName} watered via Bayesian', fontSize: 16);
        return true;
      } else {
        await Fluttertoast.showToast(msg: '❌ Bayesian error: ${response.statusCode}', fontSize: 16);
        return false;
      }
    } catch (e) {
      await Fluttertoast.showToast(msg: '❌ Bayesian server unreachable', fontSize: 16);
      return false;
    }
  }

  Future<void> stopWatering(PlantData plant) async {
    try {
      await http.post(
        Uri.parse('${settings.apiUrl}/command'),
        body: Command(target: plant.target, action: Action.STOP).toJson(),
      ).timeout(const Duration(seconds: 10));
      plant.isWatering = false;
      notifyListeners();
    } catch (e) {
      log('Stop watering error: $e');
    }
  }
}