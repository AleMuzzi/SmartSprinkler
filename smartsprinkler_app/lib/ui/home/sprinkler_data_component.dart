import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';
import 'package:smartsprinkler_app/ui/home/sprinkler_data_component_viewmodel.dart';


class SprinklerDataComponent extends StatefulWidget {
  final Sprinkler sprinkler = Sprinkler();
  SprinklerDataComponent({super.key, required this.viewModel});

  final SprinklerDataComponentViewModel viewModel;

  @override
  State<SprinklerDataComponent> createState() => _SprinklerDataComponentState();
}

class _SprinklerDataComponentState extends State<SprinklerDataComponent> {

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // show the data contained in widget.viewModel.sprinklerData
        Text('Air Humidity: ${widget.viewModel.sprinklerData.airHumidity}%', style: TextStyle(fontSize: 24)),
        Text('Air Temperature: ${widget.viewModel.sprinklerData.airTemperature}°C', style: TextStyle(fontSize: 24)),
        // Text('Soil Moisture: ${widget.viewModel.sprinklerData.soilMoisture}%', style: TextStyle(fontSize: 24)),
        Text('Water Pump: ${widget.viewModel.sprinklerData.waterPump}', style: TextStyle(fontSize: 24)),
      ],
    );
  }
}
