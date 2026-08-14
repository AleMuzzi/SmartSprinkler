import 'dart:async';
import 'dart:convert';
import 'dart:developer';

import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/data/settings.dart';

import '../../data/sprinkler.dart';

class SprinklerDataComponentViewModel {
  Timer? _timer;
  Settings settings = Settings();

  SprinklerDataComponentViewModel() {
    _fetchSprinklerData();

    // Set up a periodic timer that calls _fetchData every 10 seconds.
    _timer = Timer.periodic(const Duration(seconds: 10), (Timer t) {
      _fetchSprinklerData();
    });
  }

  void dispose() {
    _timer?.cancel();
  }

  Sprinkler sprinklerData = Sprinkler();

  Future<void> _fetchSprinklerData() async {
    // Pull the latest ESP snapshot from the Bayesian server (which
    // caches whatever it saw during its inference cycles). The app no
    // longer hits the ESP directly for /status.
    final response = await http.get(
      Uri.parse("${settings.bayesianUrl}/api/esp/status"),
    ).timeout(const Duration(seconds: 5));

    if (response.statusCode == 200) {
      try {
        Map<String, dynamic> body = {};
        body = response.body.isNotEmpty ? jsonDecode(response.body) : {};
        sprinklerData.updateWithJson(body);
      } catch (e) {
        log("Error parsing JSON: $e");
      }
    }
  }
}
