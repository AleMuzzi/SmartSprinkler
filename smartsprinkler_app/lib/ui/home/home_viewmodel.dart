import 'dart:async';
import 'dart:convert';
import 'dart:developer';

import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';

import '../../data/settings.dart';
import 'package:fluttertoast/fluttertoast.dart';


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
      await Fluttertoast.showToast(msg: "✅ Command executed!", fontSize: 16.0);
    } else {
      try {
        Map<String, dynamic> body = {};
        body = response.body.isNotEmpty ?  Map<String, dynamic>.from(jsonDecode(response.body)) : {};
        final msg = body["message"] ?? "unknown error";
        if (msg.toString().contains("blocked")) {
          Sprinkler().blockedAmountMl = 0;
          await Fluttertoast.showToast(
            msg: "⛔ Water blocked — tap alert for details",
            fontSize: 16.0,
            toastLength: Toast.LENGTH_LONG,
          );
        } else {
          await Fluttertoast.showToast(msg: "Error ${response.statusCode}: $msg", fontSize: 16.0, toastLength: Toast.LENGTH_LONG);
        }
      } catch (e) {
        await Fluttertoast.showToast(msg: "Error ${response.statusCode}: ${response.body}", fontSize: 16.0, toastLength: Toast.LENGTH_LONG);
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
        await Fluttertoast.showToast(msg: "✅ Watered via Bayesian server!", fontSize: 16.0);
      } else {
        await Fluttertoast.showToast(msg: "Bayesian error ${response.statusCode}", fontSize: 16.0);
      }
    } catch (e) {
      log("Bayesian server unreachable: $e");
      await Fluttertoast.showToast(msg: "⚠️ Bayesian server unreachable, no watering", fontSize: 16.0, toastLength: Toast.LENGTH_LONG);
    }
  }
}
