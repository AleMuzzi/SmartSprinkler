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

    // Set up a periodic timer that calls _fetchData every 5 seconds.
    _timer = Timer.periodic(const Duration(seconds: 1), (Timer t) {
      _fetchSprinklerData();
    });
  }

  void dispose() {
    _timer?.cancel();
  }

  Sprinkler sprinklerData = Sprinkler();

  Future<void> _fetchSprinklerData() async {
    final response = await http.get(Uri.parse("${settings.apiUrl}/status"));

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
