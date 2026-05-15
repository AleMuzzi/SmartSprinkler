import 'dart:collection';

import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';
import 'package:smartsprinkler_app/ui/home/sprinkler_data_component.dart';
import 'package:smartsprinkler_app/ui/home/sprinkler_data_component_viewmodel.dart';

import '../page.dart';

class HomePage extends PageWidget {
  const HomePage({super.key, required this.viewModel}) : super(title: "🌧️  Irrigation Control");

  final HomePageViewModel viewModel;

  @override
  State<HomePage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<HomePage> {
  Target? selectedPlant = Target.PEPERONCINO;
  Sprinkler sprinkler = Sprinkler();
  SprinklerDataComponentViewModel sprinklerDataComponentViewModel = SprinklerDataComponentViewModel();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40.0, vertical: 20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              const SizedBox(height: 20),
              Container(
                alignment: Alignment.center,
                child: ListenableBuilder(
                  listenable: sprinkler,
                  builder: (BuildContext context, Widget? child) {
                    return SprinklerDataComponent(viewModel: sprinklerDataComponentViewModel);
                  },
                ),
              ),
              Container(
                padding: const EdgeInsets.only(bottom: 50.0),
                color: Theme.of(context).colorScheme.surface.withOpacity(0.5),
                alignment: Alignment.bottomCenter,
                child: Column(
                  children: [
                    DropdownButton<Target>(
                      value: selectedPlant,
                      hint: const Text('Scegli una pianta'),
                      isExpanded: true,
                      items: Target.values.map((Target target) {
                        return DropdownMenuItem<Target>(
                          value: target,
                          child: Text(target.name),
                        );
                      }).toList(),
                      onChanged: (newValue) {
                        setState(() {
                          selectedPlant = newValue!;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text("Log to Bayesian server"),
                        const SizedBox(width: 8),
                        Switch(
                          value: widget.viewModel.notifyBayesian,
                          onChanged: (value) {
                            setState(() {
                              widget.viewModel.notifyBayesian = value;
                            });
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: selectedPlant != null
                          ? () { widget.viewModel.startIrrigation(selectedPlant!); }
                          : null,
                      child: const Text('Start Irrigation'),
                    ),
                    const SizedBox(height: 15),
                    ElevatedButton(
                      onPressed: selectedPlant != null
                          ? () { widget.viewModel.stopIrrigation(selectedPlant!); }
                          : null,
                      child: const Text('Stop Irrigation'),
                    ),
                    const SizedBox(height: 60),
                  ],
                )
              ),
            ],
          ),
        ),
      ),
    );
  }
}
