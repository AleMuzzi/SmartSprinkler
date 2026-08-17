import 'dart:async';
import 'dart:convert';
import 'dart:developer';

import 'package:flutter/material.dart' hide Action;
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
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
  Timer? _healthTimer;
  Timer? _bayesianTimer;
  Timer? _cisternTimer;
  Timer? _serviceTimer;
  bool _disposed = false;
  List<PlantData> _plants = [];
  List<BayesianPlantStatus> _plantStatuses = [];
  double _averageProbabilityOfNeed = 0.0;
  WeatherData? _weather;
  ConnectivityStatus _espStatus = ConnectivityStatus.checking;
  ConnectivityStatus _bayesianStatus = ConnectivityStatus.checking;
  String? _espFirmwareVersion;

  List<PlantData> get plants => _plants;
  List<BayesianPlantStatus> get plantStatuses => _plantStatuses;
  double get averageProbabilityOfNeed => _averageProbabilityOfNeed;
  WeatherData? get weather => _weather;
  ConnectivityStatus get espStatus => _espStatus;
  ConnectivityStatus get bayesianStatus => _bayesianStatus;
  String? get espFirmwareVersion => _espFirmwareVersion;
  bool _servicePaused = false;
  bool get servicePaused => _servicePaused;

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
    _fetchEspHealth();
    _fetchEspStatus();
    _fetchBayesianStatus();
    _fetchWeatherStatus();
    _fetchCisternStatus();
    _fetchServiceConfig();

    _healthTimer = Timer.periodic(const Duration(seconds: 10), (_) => _fetchEspHealth());
    _espTimer = Timer.periodic(const Duration(seconds: 10), (_) => _fetchEspStatus());
    _bayesianTimer = Timer.periodic(const Duration(seconds: 30), (_) => _fetchBayesianStatus());
    Timer.periodic(const Duration(minutes: 2), (_) => _fetchWeatherStatus());
    _cisternTimer = Timer.periodic(const Duration(seconds: 10), (_) => _fetchCisternStatus());
    _serviceTimer = Timer.periodic(const Duration(seconds: 30), (_) => _fetchServiceConfig());
  }

  @override
  void dispose() {
    _disposed = true;
    _espTimer?.cancel();
    _healthTimer?.cancel();
    _bayesianTimer?.cancel();
    _cisternTimer?.cancel();
    _serviceTimer?.cancel();
    super.dispose();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  Future<void> fetchEspHealth() => _fetchEspHealth();
  Future<void> fetchEspStatus() => _fetchEspStatus();
  Future<void> fetchBayesianStatus() => _fetchBayesianStatus();
  Future<void> fetchWeatherStatus() => _fetchWeatherStatus();
  Future<void> fetchCisternStatus() => _fetchCisternStatus();
  Future<void> fetchServiceConfig() => _fetchServiceConfig();

  /// Pings the ESP directly on /health every few seconds to keep the
  /// online indicator honest, regardless of what the Bayesian server
  /// last cached for /api/esp/status.
  Future<void> _fetchEspHealth() async {
    debugPrint('[_fetchEspHealth] URL: ${settings.apiUrl}/health');
    try {
      final response = await http.get(
        Uri.parse('${settings.apiUrl}/health'),
      ).timeout(const Duration(seconds: 5));

      _espStatus = response.statusCode == 200
          ? ConnectivityStatus.connected
          : ConnectivityStatus.disconnected;

      if (response.statusCode == 200) {
        try {
          final body = jsonDecode(response.body);
          if (body is Map<String, dynamic> && body['version'] is String) {
            _espFirmwareVersion = body['version'];
          }
        } catch (_) {
          // Non-JSON / unexpected health payload — keep the last known version.
        }
      }
    } catch (e) {
      log('ESP health check error: $e');
      _espStatus = ConnectivityStatus.disconnected;
    }
    _notify();
  }

  Future<void> _fetchEspStatus() async {
    // Status comes from the Bayesian server, which caches the latest
    // payload it observed during its inference / manual-water cycles.
    // We no longer hit the ESP directly for /status — only /command goes
    // there. Connectivity is decided by [_fetchEspHealth] instead.
    debugPrint('[_fetchEspStatus] URL: ${settings.bayesianUrl}/api/esp/status');
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/esp/status'),
      ).timeout(const Duration(seconds: 5));

      debugPrint('[_fetchEspStatus] status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        if (json.isEmpty) return; // server hasn't observed the ESP yet
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
        final activePlantStr = activePlant is String ? activePlant : activePlant?.toString();
        if (activePlantStr != null && activePlantStr != 'null' && activePlantStr.isNotEmpty) {
          for (var plant in _plants) {
            plant.isWatering = plant.target.name == activePlantStr;
          }
        } else {
          for (var plant in _plants) {
            plant.isWatering = false;
          }
        }
      }
    } catch (e) {
      log('ESP status fetch error: $e');
    }
    _notify();
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
    if (value is String) {
      if (value == 'nan' || value == 'null' || value.isEmpty) return 0.0;
      return double.tryParse(value) ?? 0.0;
    }
    return 0.0;
  }

  Future<void> _fetchBayesianStatus() async {
    debugPrint('[_fetchBayesianStatus] URL: ${settings.bayesianUrl}/api/plants/status');
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/plants/status'),
      ).timeout(const Duration(seconds: 10));

      debugPrint('[_fetchBayesianStatus] status code: ${response.statusCode}');
      debugPrint('[_fetchBayesianStatus] body: ${response.body.substring(0, response.body.length.clamp(0, 200))}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;

        final plantsJson = json['plants'] as List<dynamic>? ?? [];
        _plantStatuses = plantsJson.map((p) => BayesianPlantStatus.fromJson(p)).toList();

        debugPrint('[_fetchBayesianStatus] plants count: ${_plantStatuses.length}');

        double sum = 0;
        int count = 0;
        for (final status in _plantStatuses) {
          debugPrint('[_fetchBayesianStatus] plant: ${status.plantId} = ${status.probabilityOfNeed}');
          if (status.plantId.isEmpty) continue;
          final plant = _plants.firstWhere(
            (pl) => pl.id == status.plantId || pl.target.name.toLowerCase() == status.plantId.toLowerCase(),
            orElse: () => PlantData(id: '', displayName: '', imageUrl: '', target: Target.NAGA_MORICH),
          );
          if (plant.id.isEmpty) continue;
          plant.probabilityOfNeed = status.probabilityOfNeed;
          sum += status.probabilityOfNeed;
          count++;
        }
        _averageProbabilityOfNeed = count > 0 ? sum / count : 0.0;
        debugPrint('[_fetchBayesianStatus] average: $_averageProbabilityOfNeed');
      }

      _bayesianStatus = response.statusCode == 200
          ? ConnectivityStatus.connected
          : ConnectivityStatus.disconnected;
    } catch (e) {
      log('Bayesian status fetch error: $e');
      _bayesianStatus = ConnectivityStatus.disconnected;
    }
    _notify();
  }

  Future<void> _fetchServiceConfig() async {
    debugPrint('[_fetchServiceConfig] URL: ${settings.bayesianUrl}/api/service/config');
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/service/config'),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final config = json['config'] as Map<String, dynamic>? ?? {};
        _servicePaused = config['paused'] == '1';
        debugPrint('[_fetchServiceConfig] paused: $_servicePaused');
      }
    } catch (e) {
      log('Service config fetch error: $e');
    }
    _notify();
  }

  Future<void> setServicePaused(bool paused) async {
    try {
      final response = await http
          .post(Uri.parse('${settings.bayesianUrl}/api/service/${paused ? 'pause' : 'resume'}'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        _servicePaused = paused;
        _notify();
        await Fluttertoast.showToast(
          msg: paused ? 'Servizio in pausa' : 'Servizio riattivato',
          fontSize: 14,
        );
      } else {
        await Fluttertoast.showToast(
          msg: 'Errore ${response.statusCode} su ${paused ? 'pause' : 'resume'}',
          fontSize: 14,
        );
      }
    } catch (e) {
      log('Service ${paused ? 'pause' : 'resume'} error: $e');
      await Fluttertoast.showToast(msg: 'Bayesian unreachable', fontSize: 14);
    }
  }

  Future<void> _fetchCisternStatus() async {
    debugPrint('[_fetchCisternStatus] URL: ${settings.bayesianUrl}/api/cistern');
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/cistern'),
      ).timeout(const Duration(seconds: 5));

      debugPrint('[_fetchCisternStatus] status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        sprinkler.updateCisternWithJson(json);
      }
    } catch (e) {
      log('Cistern status fetch error: $e');
    }
    _notify();
  }

  Future<void> _fetchWeatherStatus() async {
    debugPrint('[_fetchWeatherStatus] URL: ${settings.bayesianUrl}/api/weather/status');
    try {
      final response = await http.get(
        Uri.parse('${settings.bayesianUrl}/api/weather/status'),
      ).timeout(const Duration(seconds: 10));

      debugPrint('[_fetchWeatherStatus] status: ${response.statusCode}');
      debugPrint('[_fetchWeatherStatus] body: ${response.body}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        _weather = WeatherData.fromJson(json);
        debugPrint('[_fetchWeatherStatus] weather: temp=${_weather?.temperature}, humidity=${_weather?.humidity}');
        // Sync the same reading into the singleton Sprinkler so widgets
        // that read airHumidity/airTemperature (e.g. SprinklerDataComponent)
        // show the server-side value rather than the raw ESP payload.
        sprinkler.updateWeatherFromServer(json);
        _notify();
      }
    } catch (e) {
      log('Weather status fetch error: $e');
    }
  }

  Future<void> waterPlantNow(PlantData plant, {bool viaBayesian = true}) async {
    if (!viaBayesian) {
      await _waterDirect(plant);
      return;
    }
    final success = await _waterViaBayesian(plant);
    if (!success && _bayesianStatus == ConnectivityStatus.disconnected) {
      await _waterDirect(plant);
      await Fluttertoast.showToast(
        msg: 'Bayesian offline — watered ${plant.displayName} directly via ESP',
        fontSize: 14,
      );
    }
  }

  Future<void> _waterDirect(PlantData plant) async {
    try {
      final response = await http.post(
        Uri.parse('${settings.apiUrl}/command'),
        body: Command(target: plant.target, action: Action.START).toJson(),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        plant.isWatering = true;
        _notify();
        await Fluttertoast.showToast(msg: 'OK: ${plant.displayName} watering started', fontSize: 16);
      } else {
        await Fluttertoast.showToast(msg: 'ESP error: ${response.statusCode}', fontSize: 16);
      }
    } catch (e) {
      await Fluttertoast.showToast(msg: 'ESP unreachable', fontSize: 16);
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
        plant.isWatering = true;
        _notify();
        await Fluttertoast.showToast(msg: 'OK: ${plant.displayName} watered via Bayesian', fontSize: 16);
        return true;
      } else {
        await Fluttertoast.showToast(msg: 'Bayesian error: ${response.statusCode}', fontSize: 16);
        return false;
      }
    } catch (e) {
      log('Bayesian water error: $e');
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
      _notify();
    } catch (e) {
      log('Stop watering error: $e');
    }
  }

  Future<void> dispenseAmount(PlantData plant, int amountMl) async {
    try {
      final response = await http.post(
        Uri.parse('${settings.apiUrl}/command'),
        body: Command(target: plant.target, action: Action.DISPENSE_SPECIFIC_AMOUNT, amount: amountMl).toJson(),
      ).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        plant.isWatering = true;
        _notify();
        await Fluttertoast.showToast(msg: 'Dispensing ${amountMl}ml for ${plant.displayName}', fontSize: 14);
      } else {
        await Fluttertoast.showToast(msg: 'ESP error: ${response.statusCode}', fontSize: 14);
      }
    } catch (e) {
      await Fluttertoast.showToast(msg: 'ESP unreachable', fontSize: 14);
    }
  }

  Future<void> runInferenceNow() async {
    try {
      final response = await http
          .post(Uri.parse('${settings.bayesianUrl}/api/inference/run'))
          .timeout(const Duration(seconds: 20));
      if (response.statusCode == 200) {
        final watered = (jsonDecode(response.body)['watered'] as Map<String, dynamic>).keys;
        await Fluttertoast.showToast(
          msg: watered.isEmpty
              ? 'Inferenza eseguita — nessuna pianta da annaffiare'
              : 'Inferenza eseguita — annaffiate: ${watered.join(', ')}',
          fontSize: 14,
        );
        await _fetchBayesianStatus();
        await _fetchEspStatus();
      } else {
        await Fluttertoast.showToast(msg: 'Inferenza fallita: ${response.statusCode}', fontSize: 14);
      }
    } catch (e) {
      await Fluttertoast.showToast(msg: 'Bayesian unreachable', fontSize: 14);
    }
  }

  static void showWaterDialog(BuildContext context, PlantData plant) {
    final vm = Provider.of<DashboardViewModel>(context, listen: false);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Water ${plant.displayName}'),
        content: const Text('How do you want to water?'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              vm.waterPlantNow(plant, viaBayesian: true);
            },
            child: const Text('Via Bayesian'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              vm.waterPlantNow(plant, viaBayesian: false);
            },
            child: const Text('Direct (ESP)'),
          ),
        ],
      ),
    );
  }
}
