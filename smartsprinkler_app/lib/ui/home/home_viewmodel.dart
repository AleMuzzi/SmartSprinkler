import 'dart:async';
import 'dart:convert';
import 'dart:developer';

import 'package:flutter/material.dart' hide Action;
import 'package:http/http.dart' as http;
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';

import '../../data/settings.dart';
import 'package:fluttertoast/fluttertoast.dart';


class HomePageViewModel {
  final Settings settings = Settings();

  HomePageViewModel();

  Future<void> commandIrrigation(Target target, Action action) async {
    // send http post request to perform/stop irrigation
    final response = await http.post(
        Uri.parse("${settings.apiUrl}/command"),
        body: Command(target: target, action: action).toJson()
    );

    if (response.statusCode == 200) {
      await Fluttertoast.showToast(msg: "✅ Command executed!", fontSize: 16.0);
    } else {
      try {
        Map<String, dynamic> body = {};
        body = response.body.isNotEmpty ?  Map<String, dynamic>.from(jsonDecode(response.body)) : {};
        await Fluttertoast.showToast(msg: "Error ${response.statusCode}: ${body["message"]}", fontSize: 16.0, toastLength: Toast.LENGTH_LONG);
      } catch (e) {
        await Fluttertoast.showToast(msg: "Error ${response.statusCode}: ${response.body}", fontSize: 16.0, toastLength: Toast.LENGTH_LONG);
      }
    }
  }

  Future<void> startIrrigation(Target target) async {
    return commandIrrigation(target, Action.START);
  }

  Future<void> stopIrrigation(Target target) async {
    return commandIrrigation(target, Action.STOP);
  }
}
