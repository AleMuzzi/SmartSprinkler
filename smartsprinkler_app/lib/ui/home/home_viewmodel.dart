import 'dart:async';
import 'dart:convert';
import 'dart:developer';

import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';

import '../../data/settings.dart';
import 'package:smartsprinkler_app/utils/toast.dart';


class HomePageViewModel {
  final Settings settings = Settings();
  bool notifyBayesian = true;

  HomePageViewModel();

  Future<void> commandIrrigation(Target target, Action action, {bool force = false}) async {
    final response = await http.post(
        Uri.parse("${settings.apiUrl}/command"),
        body: Command(target: target, action: action, force: force).toJson()
    );

    if (response.statusCode == 200) {
      showAppToast("✅ Command executed!");
    } else {
      try {
        Map<String, dynamic> body = {};
        body = response.body.isNotEmpty ?  Map<String, dynamic>.from(jsonDecode(response.body)) : {};
        final msg = body["message"] ?? "unknown error";
        if (msg.toString().contains("blocked")) {
          Sprinkler().blockedAmountMl = 0;
          showAppToast(
            "⛔ Water blocked — tap alert for details",
          );
        } else {
          showAppToast("Error ${response.statusCode}: $msg");
        }
      } catch (e) {
        showAppToast("Error ${response.statusCode}: ${response.body}");
      }
    }
  }

  Future<void> forceIrrigation(Target target, Action action) async {
    return commandIrrigation(target, action, force: true);
  }

  Future<void> startIrrigation(Target target) async {
    if (notifyBayesian) {
      return _waterViaBayesianServer(target);
    }
    return commandIrrigation(target, Action.START);
  }

  Future<void> stopIrrigation(Target target) async {
    return commandIrrigation(target, Action.STOP);
  }

  Future<void> _waterViaBayesianServer(Target target) async {
    try {
      final payload = jsonEncode({"plant_type": target.name.toLowerCase()});
      final response = await http.post(
        Uri.parse("${settings.bayesianUrl}/api/plants/manual-water"),
        headers: {"Content-Type": "application/json"},
        body: payload,
      ).timeout(const Duration(seconds: 15));
      if (response.statusCode == 200) {
        showAppToast("✅ Watered via Bayesian server!");
      } else {
        showAppToast("Bayesian error ${response.statusCode}");
      }
    } catch (e) {
      log("Bayesian server unreachable: $e");
      showAppToast("⚠️ Bayesian server unreachable, no watering");
    }
  }
}