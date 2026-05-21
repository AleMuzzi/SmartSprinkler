import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';
import 'package:smartsprinkler_app/ui/home/low_water_alert_page.dart';
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
  Target? selectedPlant = Target.NAGA_MORICH;
  Sprinkler sprinkler = Sprinkler();
  SprinklerDataComponentViewModel sprinklerDataComponentViewModel = SprinklerDataComponentViewModel();

  @override
  void dispose() {
    sprinklerDataComponentViewModel.dispose();
    super.dispose();
  }

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
              ListenableBuilder(
                listenable: sprinkler,
                builder: (context, _) {
                  if (!sprinkler.waterLowAlert) return const SizedBox.shrink();
                  return Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade100,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.orange.shade700),
                    ),
                    child: InkWell(
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const LowWaterAlertPage()),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                          const SizedBox(width: 8),
                          Expanded(child: Text("⚠️ Water tank low — irrigation disabled", style: TextStyle(color: Colors.orange.shade900))),
                          const Icon(Icons.chevron_right, color: Colors.orange),
                        ],
                      ),
                    ),
                  );
                },
              ),
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
                color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.5),
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
